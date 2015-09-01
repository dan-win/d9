# fix division problem:
from __future__ import division

import csv

import math
import random
import itertools

import sys
try:
    import matplotlib.pyplot as plt
    import numpy
except ImportError:
    print "Requires matplotlib and numpy modules!"
    sys.exit(1)

try:
    # if C version is available:
    import cPickle as pickle
except ImportError:
    # Otherwise import pure-Python version:
    import pickle

class ENumSequenceError(Exception):
    "Generic error in num sequence object"
    pass

class NumSequence(object):
    """
    Sequnce of typed numbers, with preserved order.
    Independent variable - zero-based index.
    Write operations: 
    - singular point: .append(); 
    - bulk copy: .copyfrom().
    Computes min, max, sum and mean values.
    >>> p = NumSequence()
    >>> p.append(10)
    Data set: min: 10, mean: 10.0, max:10, sum: 10, count: 1
    >>> len(p)
    1
    >>> p.append(20).append(30).append(40)
    Data set: min: 10, mean: 25.0, max:40, sum: 100, count: 4
    >>> len(p)
    4
    >>> p.min
    10
    >>> p.max
    40
    >>> len(p)
    4
    >>> p.mean
    25.0
    >>> p.x
    (0, 1, 2, 3)
    >>> p.y
    (10, 20, 30, 40)
    >>> p.store('profile.dat')
    >>> pnew = NumSequence()
    >>> pnew.load('profile.dat')
    >>> p.len
    4
    >>> p.min
    10
    >>> p.max
    40
    >>> y = p.selectrandom()
    >>> p.min <= y <= p.max
    True
    """

    stored_attrs = ['_label', '_values']

    def __init__(self, label='Data set'):
        self._label = label
        self._values = []
    
    def store(self, filename):
        "Store data for further playback"
        data = {}
        for name in self.stored_attrs:
            data[name] = getattr(self, name)
        with open(filename, "wb") as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

    def load(self, filename):
        "Load data for further playback"
        data = None
        with open(filename, "rb") as f:
            data = pickle.load(f)
        for name, value in data.iteritems():
            setattr(self, name, value)

    def append(self, value):
        "Add new value to serie"
        self._values.append(value)
        return self # for chaining
    
    def selectrandom(self):
        if self.len == 0:
            raise ENumSequenceError('Cannot select random element from empty set.')
        index = random.randrange(0, self.len)
        return self.y[index]
    
    def _update(self):
        "Update before return values, if necessary"
        pass

    def fromlist(self, data):
        self._values = list(data)
        self._update()
        return self # for chaining

    def copyfrom(self, source):
        "Set object data from other object"
        if not isinstance(source, NumSequence):
            raise ENumSequenceError \
                ('Cannot use .copyfrom(): source is not NumSequence instance!')
        self.fromlist(source.itervalues())
        return self # for chaining

    def x_slice(self, min=None, max=None, label=None):
        "Return sliced instance where min<X<max"
        self._update()
        imin = min or 0
        imax = max or (len(self) - 1)
        # make instance of same class:
        buff = self.__class__( \
            label or "Slice of {}: {} <= X <= {}".format(self.label, imin, imax)) 
        buff.fromlist(self._values[imin:imax+1])
        return buff

    def y_slice(self, min=None, max=None, label=None):
        "Return sliced instance where min<Y<max"
        self._update()
        imin = 0
        imax = len(self) - 1
        data = self.y
        if min is not None:
            while data[imin] < min and imin < imax:
                imin += 1
        if max is not None:
            while data[imax] > max and imax != 0:
                imax -= 1
        # make instance of same class:
        buff = self.__class__( \
            label or "Slice of {}: {} < Y < {}".format(self.label, imin, imax)) 
        buff.fromlist(self._values[imin:imax+1])
        return buff

    @property
    def label(self):
        "Label for data set"
        return self._label
    
    @property
    def len(self):
        return len(self._values)
    
    @property
    def x(self):
        "Return list of 'X' values"
        return tuple(self.iterkeys())
    
    @property
    def y(self):
        "Return list of 'Y' values"
        return tuple(self.itervalues())
    
    @property
    def min(self):
        "Min value of dependent variable (like min(Y))"
        return min(self.itervalues())
    
    @property
    def max(self):
        "Max value of dependent variable (like max(Y))"
        return max(self.itervalues())
    
    @property
    def sum(self):
        "Sum value of dependent variable (like sum(Y))"
        return sum(self.itervalues())
    
    @property
    def mean(self):
        "Mean value of dependent variable (like mean(Y))"
        try:
            return self.sum / len(self)
        except ZeroDivisionError:
            return 0
    
    def iteritems(self):
        """
        Iterate over dependent variable (like 'Y').
        Method must be applicable for copying 
        via object.copyfrom(otherobject).
        Method must be overriden for objects
        where 'X' representation differs from index of value.
        """
        self._update()
        return iter(self._values)

    def iterkeys(self):
        "Iterate over independent variable (like 'X')"
        self._update()
        return xrange(0, len(self._values))

    def itervalues(self):
        "Iterate over dependent variable (like 'Y')"
        self._update()
        return iter(self._values)
    
    def __str__(self):
        "Return string representation of object"
        return '{}: min: {}, mean: {}, max:{}, sum: {}, count: {}' \
            .format(self.label, self.min, self.mean, self.max, self.sum, len(self))
    
    def __repr__(self):
        "Return representation of object (here is 'string')"
        return self.__str__()
        
    def __call__(self):
        "Make object callable"
        return (self.x, self.y)
    
    def __len__(self):
        "Return length by len(object)"
        return len(self._values)

from heapq import heappush

class NumSet(NumSequence):
    """
    Sorted sequence from min to max value.
    Independent variable - zero-based index.
    >>> p = NumSet()
    >>> p.append(10)
    Data set: min: 10, mean: 10.0, max:10, sum: 10, count: 1
    >>> len(p)
    1
    >>> p.append(5).append(20).append(10).append(10)
    Data set: min: 5, mean: 11.0, max:20, sum: 55, count: 5
    >>> p.x
    (0, 1, 2, 3, 4)
    >>> p.y
    (5, 10, 10, 10, 20)
    >>> p.append(20).append(40).append(30).y
    (5, 10, 10, 10, 20, 20, 30, 40)
    >>> len(p)
    8
    >>> p = p.y_slice(30, 40)
    >>> p()
    ((0, 1), (30, 40))
    """
    def __init__(self, label='Data set'):
        NumSequence.__init__(self, label=label)
        self._needsorting = False

    def _update(self):
        if self._needsorting:
            self._values.sort() # <- fix problem with unsorted tail of heap
            self._needsorting = False # clear "sorting" flag
        
    def append(self, value):
        heappush(self._values, value)
        self._needsorting = True
        return self # for chaining
        
class NumXY(NumSet):
    """
    Store for list of (x, y) values,
    where x can be a float number also.
    Compute min, max and mean values.
    >>> p = NumXY()
    >>> p.append(0, 10)
    Data set: min: 10, mean: 10, max:10, sum: 0, count: 1
    >>> len(p)
    1
    >>> p.append(10, 20)
    Data set: min: 10, mean: 15.0, max:20, sum: 150.0, count: 2
    >>> len(p)
    2
    >>> p.append(20, 30).append(30,40).append(40,100)
    Data set: min: 10, mean: 36.25, max:100, sum: 1450.0, count: 5
    >>> p1 = p.x_slice(30, 40)
    
    >>> p1.min
    40
    >>> p1.max
    100
    >>> p.mean
    36.25
    >>> p.x
    (0, 10, 20, 30, 40)
    >>> p.y
    (10, 20, 30, 40, 100)
    """

    def append(self, x, y):
        return NumSet.append(self, (x, y)) # for chaining

    def copyfrom(self, source):
        "Set object data from other object"
        if not isinstance(source, NumSequence):
            raise ENumSequenceError \
                ('Cannot use .copyfrom(): source is not NumSequence instance!')
        self.fromlist(source.iteritems())
        return self # for chaining

    def x_slice(self, min=None, max=None, label=None):
        "Return sliced instance where min<=X<=max"
        self._update()
        findmin =  (min is not None) 
        findmax = (max is not None)
        imin = 0
        imax = 0 if findmax else len(self) - 1
        # make instance of same class:
        buff = self.__class__( \
            label or "Slice of {}: {} < X < {}".format(self.label, imin, imax))
        for x, y in self.iteritems():
            if findmin and x < min: 
                imin += 1
            if findmax and x <= max: 
                imax += 1 
        buff.fromlist(self._values[imin:imax])
        return buff

    def iterkeys(self):
        "Iterate over independent variable (like 'X')"
        self._update()
        return iter([x for x, y in self._values])

    def itervalues(self):
        "Iterate over dependent variable (like 'Y')"
        self._update()
        return iter([y for x, y in self._values])
    
    @property
    def sum(self):
        "Integrated value of dependent variable"
        if len(self) == 0:
            return 0

        getx = lambda point: point[0]
        gety = lambda point: point[1]
        ds = lambda p0, p1: ((gety(p0)+gety(p1))/2) * (getx(p1)-getx(p0))

        return sum(map(ds, self._values[0:-1], self._values[1:]))
    
    @property 
    def mean(self):
        "Compute mean value of function on X range"
        try:
            # compute mean as integral by Y divided by total range of X:
            return self.sum / (self._values[-1][0] - self._values[0][0])
        except:
            # if X range is near zero - return first Y value
            return self._values[-1][1]

class Histogram(NumXY):
    """
    Frequency distribution foe numeric sequence.
    >>> p = NumSet()
    >>> p.fromlist([0,10,10,10,10,20,20, 30, 40])
    Data set: min: 0, mean: 16.6666666667, max:40, sum: 150, count: 9
    >>> p.y
    (0, 10, 10, 10, 10, 20, 20, 30, 40)
    >>> h = Histogram(label='test Histogram', source=p, bins=3)
    >>> h._values
    [(10.0, 5), (20.0, 2), (30.0, 1), (40.0, 1)]
    >>> h
    
    """
    def __init__(self, label="Histogram", source=None, bins=10):
        NumXY.__init__(self, label=label)
        #~ print 'label:', label
        #~ print 'source', source
        if isinstance(source, NumSequence) and source.len > 0: 
            self._build(source.y, bins)
        else:
            raise ENumSequenceError('Cannot create histogram from empty object')


    def _build(self, values, bins):
        yrange = (max(values)-min(values))
        delta = math.ceil(yrange/bins)
        yremainder = yrange - delta * bins
        while yremainder != 0:
            # find nearest divider
            bins += 1
            delta = math.ceil(yrange/bins)
            yremainder = yrange - delta * bins
            
        vertices = {}
        values = list(values)[:]
        values.sort()
        
        v0 = values[0] + delta
        for v in values:
            if v > v0:
                v0 += delta
            if v0 not in vertices:
                vertices[v0] = 1
            else:
                vertices[v0] += 1
        
        self._values = list(vertices.iteritems())
        self._values.sort()
        
    def append(self, value):
        raise NotImplemented("Histogram object supports only bulk assignments!")

    def fromlist(self, data, grouplength):
        raise NotImplemented("Histogram object supports only bulk assignments!")

    def copyfrom(self, source):
        raise NotImplemented("Histogram object supports only bulk assignments!")
        
    @property
    def sum(self):
        "Sum value of dependent variable (like sum(Y))"
        print type(self)
        return sum(map(lambda x, y: x * y, self.iterkeys(), self.itervalues()))
    
    @property
    def mean(self):
        "Mean value of dependent variable (like mean(Y))"
        try:
            return self.sum / sum(self.x)
            #~ return self.sum / (max(self.x)-min(self.x))
        except ZeroDivisionError:
            return 0

    @property
    def bins(self):
        return len(self._values)
    
    def __call__(self):
        """
        Use this method for direct output
        into pyplot charts: 
        *p.call() --> x[], y[]
        """
        return zip(*self._values)

if __name__ == '__main__':
    import doctest
    doctest.testmod()