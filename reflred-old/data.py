# This program is public domain
"""
Data was the initial foray into a data representation for reflectometry,
and in particular for polarization correction, which was the first task.

It's main attributes is that it defines standard names for the data
axes x,y,z and values v, as well as a holder for labels and units.

Many of the ideas of data are preserved and live on in refldata.  At
some point refldata may be made to inherit from data, but for data
will act as a platform for developing plotting ideas, and is not part
of the main reflectometry code.
"""
from __future__ import division
import numpy as np

def edges_from_centers(x):
    """
    Given a series of bin centers, compute the bin edges corresponding
    to those centers assuming the edeges are mid-way between the centers.
    Note: assumes the bins are the same width.  If this is not the case,
    there is insufficient information to uniquely reconstruct the edges
    given the centers.
    """
    z = np.zeros(len(x)+1)
    z[1:-1] = centers_from_edges(x)
    z[0] = x[0] - (z[1]-x[0])
    z[-1] = x[-1] + (x[-1]-z[-2])
    return z

def centers_from_edges(x):
    """
    Given a series of bin edges, return the bin centers.
    """
    return (x[:-1]+x[1:])/2.

def dims(a):
    """
    Printable form for matrix dimensions.
    """
    return "x".join([str(v) for v in a.shape])

def dict2text(d,indent=0):
    """
    Display the contents of a dictionary with some formatting.
    """
    keys = d.keys()
    keys.sort()
    lines = []
    for key in keys:
        val = d[key]
        if isinstance(val,dict):
            text = "\n"+dict2text(val,indent+2)
        elif isinstance(val,np.ndarray):
            text = "array size " + dims(val)
        else:
            text = str(val)
        lines.append(" "*indent + key + ": " + text)
    return "\n".join(lines)


class _Data(object):
    """
    Data object.

    For one-dimensional data use x,v.
    For two and three dimensional data use x,y,z,v.

    Multi-dimensional data can be regular or irregular.  If it is irregular,
    the size of x,y,z must match the size of z.  If it is regular,
    the size of each vector x,y,z must match the corresponding dimension of v.

    Note: for reflectivity the natural dimensions are x='Qz',y='Qx',z='Qy'
    """
    x,dx = None,None  # type: np.ndarray, np.ndarray
    y,dy = None,None  # type: np.ndarray, np.ndarray
    z,dz = None,None  # type: np.ndarray, np.ndarray
    v,variance = None,None  # type: np.ndarray, np.ndarray
    xlabel,xunits='x',None  # type: str, str
    ylabel,yunits='y',None  # type: str, str
    zlabel,zunits='z',None  # type: str, str
    vlabel,vunits='v',None  # type: str, str

    # Store variance but allow 1-sigma uncertainty interface
    def _getdv(self): return np.sqrt(self.variance)
    def _setdv(self,dv): self.variance = dv**2
    dv = property(_getdv,_setdv,doc='1-sigma uncertainty')

    # Store edges and retrieve centers
    def _getxedges(self):
        return edges_from_centers(self.x)
    def _setxedges(self,t):
        self.x = centers_from_edges(t)
    xedges = property(_getxedges,_setxedges,doc='x edges')
    def _getyedges(self):
        return edges_from_centers(self.y)
    def _setyedges(self,t):
        self.y = centers_from_edges(t)
    yedges = property(_getyedges,_setyedges,doc='y edges')
    def _getzedges(self):
        return edges_from_centers(self.z)
    def _setzedges(self,t):
        self.z = centers_from_edges(t)
    zedges = property(_getzedges,_setzedges,doc='z edges')

    # Set attributes on initialization
    def __init__(self,**kw):
        self.messages = []
        for k,v in kw.items(): setattr(self,k,v)

    def log(self,msg):
        """Record corrections that have been applied to the data"""
        self.messages.append(msg)

    def __str__(self):
        return "Data(%s)"%(dims(self.v))

    def interp(self, x):
        v = np.interp(self.x, self.v, x)
        dv = np.sqrt(np.interp(self.x, self.dv**2, x))
        return v,dv

class _PolarizedData(object):
    """
    Polarized data object.  This holds all four cross sections of a
    polarized measurement, and provides operations for aligning and
    transforming the cross sections.
    """

    xlabel,xunits='Qz','inv A'
    ylabel,yunits='Qx','inv A'
    zlabel,zunits='Qy','inv A'
    vlabel,vunits='Reflectivity',None

    def __init__(self, **kw):
        self.pp,self.pm,self.mp,self.mm = _Data(),_Data(),_Data(),_Data()
        self.set(**kw)
        self.messages = []

    def set(self,**kw):
        """Set a number of attributes simultaneously"""
        for k,v in kw.items():
            if hasattr(self,k):
                setattr(self,k,v)
            else:
                raise AttributeError("could not set %r in PolarizedData"%k)

    def __str__(self):
        return "\n".join(["++"+str(self.pp),"--"+str(self.mm),
                          "+-"+str(self.pm),"-+"+str(self.mp)])

    def ispolarized(self):
        """Indicates that the data is polarized data."""
        return True

    def isaligned(self):
        """Test if all four cross sections have the same Q values."""
        # TODO: perform the check (monoref only)
        return True

    def log(self,msg):
        """Record corrections that have been applied to the data"""
        self.messages.append(msg)

    def spin_asymmetry(self):
        """
        Return the spin asymmetry for the pp and mm cross sections.
        This is a Data object with one data line.

        TODO: support multidimensional data
        """
        if (len(self.pp.x) == len(self.mm.x)
            and np.linalg.norm((self.pp.x - self.mm.x)/self.pp.dx) < tol):
            x = self.pp.x
            dx = self.pp.dx
            pp, Vpp = self.pp.v, self.pp.variance
            mm, Vmm = self.mm.v, self.mm.variance
        else:
            # TODO: implement matching and interpolation
            x = match_ordinal(self.pp,self.mm)
            pp, dpp = self.pp.interp(x)
            mm, dmm = self.mm.interp(x)
        v = (pp-mm)/(pp+mm)
        V = v**2 * ( (1/(pp-mm) + 1/(pp+mm))**2 * dpp**2
                     + (1/(pp-mm) + 1/(pp+mm))**2 * dmm**2 )
        result = Data(x=x,v=v,variance=V,
                      xlabel=self.xlabel, xunits=self.xunits,
                      vlabel="Spin asymmetry", vunits=None)
        return result

# ======================== Sample data ============================
def refl(n=100,noise=0.02):
    """
    Example 1D data: fresnel reflectivity for neutrons off silicon
    n = number of data points
    noise = relative error in simulated data points
    """
    Q = np.linspace(0.,0.5,n)
    dQ = Q*0.001
    f = np.sqrt(Q**2 - 16*np.pi*2.07e-6 + 0j)
    R = np.abs( (Q-f)/(Q+f) )**2
    dR = noise*R
    R = R + dR*np.random.randn(n)
    data = _Data(x=Q,dx=dQ,v=R,dv=dR,xlabel='Q',xunits='inv A',vlabel='R')
    return data

def peaks(n=40,noise=0.02):
    """Example 2D data: peaks function"""
    nr,nc = n,n+5
    x = np.linspace(-3,3,nr)
    y = np.linspace(-3,3,nc)
    [X,Y] = np.meshgrid(x,y)
    v = 3*(1-X)**2*np.exp(-X**2 - (Y+1)**2) \
          - 10*(X/5 - X**3 - Y**5)*np.exp(-X**2-Y**2) \
          - 1/3*np.exp(-(X+1)**2 - Y**2)
    v = v + noise*np.random.randn(nc,nr)
    data = _Data(x=x,y=y,v=v)
    return data

def noise2d(n=40,noise=0.02,bkg=1e-10):
    """Example 2D data: positive noise"""
    nr,nc = n,n+1
    x = np.linspace(0,1,nr)
    y = np.linspace(0,1,nc)
    v = np.abs(noise*np.random.randn(nc,nr))+bkg
    data = _Data(x=x,y=y,v=v)
    return data

def noisepol2d(n=40):
    """Example 2D polarized data: positive noise"""
    pp = noise2d(n,noise=0.05)
    pm = noise2d(n,noise=0.3); pm.v *= 0.2;
    mp = noise2d(n,noise=0.3); mp.v *= 0.2;
    mm = noise2d(n,noise=0.05)
    data = _PolarizedData()
    data.pp,data.mm = pp,mm
    data.pm,data.mp = pm,mp
    return data

def peakspol(n=40):
    """Example 2D polarized data: peaks function"""
    pp = peaks(n,noise=0.05)
    pm = peaks(n,noise=0.3); pm.v *= 0.4;
    mp = peaks(n,noise=0.3); mp.v *= 0.4;
    mm = peaks(n,noise=0.05)
    data = _PolarizedData()
    data.pp,data.mm = pp,mm
    data.pm,data.mp = pm,mp
    return data

def demo():
    """Smoke test demo"""
    d = noisepol2d(n=3)
    print "polarized 2D noise:",d
    print "++",d.pp,d.pp.v
    print "--",d.mm,d.mm.v
    print "+-",d.pm,d.pm.v
    print "-+",d.mp,d.mp.v
    print "x,y",d.mp.x,d.mp.y
    print "edges x,y",d.mp.xedges,d.mp.yedges

if __name__ == "__main__":
    demo()
    #print refl()
