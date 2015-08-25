# fix division problem:
from __future__ import division

import csv

import math
import random

import sys
try:
    import matplotlib.pyplot as plt
    import numpy
except ImportError:
    print "Requires matplotlib and numpy modules installed!"
    sys.exit(1)

data = []

def timefromtimestr(s):
    """ Decode from text like 00:00:00"""
    if len(s) == 0:
        return None
    h, m, s = [int(v) for v in s.split(':')]
    return 3600*h + 60 *m + s

def timefromdatestr(s):
    """ Decode from text like <date><space>00:00:00"""
    if len(s) == 0:
        return None
    return timefromtimestr(s.split(' ')[1])

def decode(d, name):
    if len(d[name]) > 0:
        return d[name]
    else:
        return None

# misc:
class Profile(object):
    """
    Count number of values "v" which belongs 
    to interval xmin + n * step .. xmin + (n+1) * step
    """
    def __init__(self, xmin, xmax, step):
        self.count = 0.0
        # margins:
        self.xmin = xmin
        self.xmax = xmax
        
        # actual values:
        self.low = None
        self.high = None
        self.mean = 0.0
        
        self.step = step
        self.x = [] # as duration
        self.y = []
        nitems = (xmax - xmin) // step
        for i in range(0, nitems):
            self.y.append(0)
            self.x.append(xmin + i * step)
                    
    def update(self, v):
        if v < self.xmin or v > self.xmax:
            return
        if self.low is None: self.low = v
        if self.high is None: self.high = v
        self.low = min(self.low, v)
        self.high = max (self.high, v)
        self.mean = self.mean * self.count
        self.count += 1.0
        self.mean = (self.mean + v) / self.count

        index = math.trunc((v - self.xmin) / self.step)
        self.y[index] += 1
    
    def __str__(self):
        return 'min: {}, mean: {}, max:{}'.format(self.low, self.mean, self.high)
    
    def __repr__(self):
        return self.__str__()
        
    def __call__(self):
        return (self.x, self.y)

class PoissonProfile(Profile):
    def __init__(self, xmin, xmax, step, k=1, lam=1):
        Profile.__init__(self, xmin, xmax, step)
        self.k = k
        self.lam = lam
    
    def update(self, v=None):
        v = numpy.random.poisson(float(self.lam))
        Profile.update(self, v)

class ExpovarianteProfile(Profile):
    def __init__(self, xmin, xmax, step, k=1, lam=1):
        Profile.__init__(self, xmin, xmax, step)
        self.k = k
        self.lam = lam
    
    def update(self, v=None):
        v = random.expovariate(float(self.lam))
        Profile.update(self, v)            

class LognormalProfile(Profile):
    def __init__(self, xmin, xmax, step, mean, sigma):
        Profile.__init__(self, xmin, xmax, step)
        self.logmean = mean
        self.logsigma = sigma
        s = numpy.random.lognormal(mean=self.logmean, sigma=self.logsigma, size=100000)
        for v in s:
            Profile.update(self, v)
    



def expovariate(k, lambd, size):
    buff = [] 
    count = 0
    while count < size:
        buff.append(k * random.expovariate(lambd))
        count += 1
    return buff


from heapq import heappush
h_duration_profile = []
h_dialing_profile = []
h_calls_profile = []
d_agents = {}

t_uptime = 0
t_service_time = 0
n_calls = 0
n_answered_calls = 0
weighted_average_call_duration = 0

vmin = 0
vmax = 2000
quantum = 2
c_duration = Profile(vmin, vmax, quantum)
c_dmodel_poisson = PoissonProfile(vmin, vmax, quantum, k = 0.5, lam = 1)
c_dmodel_expovariate = ExpovarianteProfile(vmin, vmax, quantum, k = 0.5, lam = 1)
c_dmodel_lognormal = LognormalProfile(vmin, vmax, quantum, mean=38, sigma = 3600)

with open('call_log.csv',  'r') as f:
    reader = csv.DictReader(f, delimiter=',')
    for line in reader:
        agent_name = line['agent_name']
        if agent_name in d_agents:
            d_agents[agent_name] += 1
        else:
            d_agents[agent_name] = 1
            
        line['classification'] = decode(line, 'classification')
        call_time = line['call_time'] = timefromdatestr(line['call_time']) 
        n_calls += 1
        heappush(h_calls_profile, call_time)
        talk_time = line['talk_time'] = timefromdatestr(line['talk_time']) 
        
        if talk_time is not None and  call_time is not None:
            dialing_time = line['dialing_time'] = talk_time - call_time
            heappush(h_dialing_profile, dialing_time) 
        else:
            dialing_time = line['dialing_time'] = None
        
        call_duration = line['call_duration'] = timefromtimestr(line['call_duration'])
        #~ if call_duration and line["classification"] != 'Voicemail':
        if call_duration and call_duration > 10:
            n_answered_calls += 1
            t_service_time += call_duration
            heappush(h_duration_profile, call_duration) 
            c_duration.update(call_duration)
            c_dmodel_poisson.update()
            c_dmodel_expovariate.update()
            #~ c_dmodel_lognormal.update()
                #~ heappush(h_calls_profile, call_time)
            weighted_average_call_duration = float(weighted_average_call_duration * \
                (n_answered_calls-1) + call_duration) / float(n_answered_calls)
        
        data.append(line)

t_uptime = data[-1]['call_time'] - data[0]['call_time']
n_agents = len(d_agents)

call_rate = float(n_calls)/float(t_uptime)
answered_call_rate = float(n_answered_calls)/float(t_uptime)

connection_rate = float(n_answered_calls)/float(n_calls)
average_call_duration =  float(t_service_time)/float(n_answered_calls)

def cuttail(data, maxval):
    i, length = 0, len(data)
    while i < length and data[i] < maxval:
        i += 1
    if i < length:
        data = data[:i]
    return data

print "Results are below, see also on the popup plot window"
print "Maximum value of call duration (sec): %f" % max(h_duration_profile)
print "Minimal value of call duration (sec): %f" % min(h_duration_profile)

print "Maximum value of dialing duration (sec * 10): %f" % max(h_dialing_profile)
print "Minimal value of dialing duration (sec * 10): %f" % min(h_dialing_profile)

print "Agents total: %i" % n_agents
print "Call-center Uptime: %i" % t_uptime
print "Man * time total: %i" % (t_uptime * n_agents)
print "Service time: %i" % t_service_time
print "Total idle time: %i" % (t_uptime * n_agents - t_service_time)

print "Idle time percent: %f" % (float(t_uptime * n_agents - t_service_time) *100 / float(t_uptime * n_agents))
print "Average idle time per agent: %f" % (float(t_uptime * n_agents - t_service_time) / float(len(d_agents)))
print "Calls total (w/o voicemail): %i" % n_calls
print "Calls answered (w/o voicemail): %i" % n_answered_calls
print "Call rate (1/sec): %f" % call_rate
print "Connection rate: %f" % connection_rate
print "Answered call rate (1/sec): %f" % answered_call_rate
print "Average call duration: %f" % average_call_duration
print "Weighted average call duration: %f" % weighted_average_call_duration


print 'Call distribution: ', c_duration
print 'Poisson model: ', c_dmodel_poisson
print 'Expovariante model: ', c_dmodel_expovariate
print 'Lognormal model: ', c_dmodel_lognormal

#~ h_duration_profile = cuttail(h_duration_profile, 25)
#~ p0 = cuttail(poisson(k=25, lam=2, size=1000), 25)
#~ e = cuttail(expovariate(average_call_duration, answered_call_rate, 1000), 25)
#~ e1 = cuttail(numpy.random.exponential(scale=0.5, size=1000), 25)
#~ e2 = cuttail(numpy.random.exponential(scale=1, size=1000), 25)
#~ e3 = cuttail(numpy.random.exponential(scale=2, size=1000), 25)

#~ plt.hist(h_duration_profile, bins=1000, histtype='step', color='b', rwidth=20, label='Duration')
#~ plt.hist(p0, bins=100, histtype='step', color='g', normed=True, rwidth=20, label='Poisson(2)')

plt.plot(*c_duration(), label = 'c_duration')
plt.plot(*c_dmodel_poisson(), label = 'c_dmodel_poisson')
plt.plot(*c_dmodel_expovariate(), label = 'c_dmodel_expovariate')
plt.plot(*c_dmodel_lognormal(), label = 'c_dmodel_lognormal')
#~ plt.fill(c_duration.x, c_dmodel_poisson.y, "g", label = 'c_dmodel_poisson')
#~ plt.hist(e, bins=100, histtype='bar', normed=True, label='Exp(0)')
#~ plt.hist(e0, bins=100, histtype='bar', normed=True, label='Exp(0)')
#~ plt.hist(e1, bins=1000, histtype='step', color='r', normed=True, label='Exp(1)')
#~ plt.hist(e2, bins=100, histtype='bar', normed=True, label='Exp(2)')
#~ plt.hist(e3, bins=100, histtype='bar', normed=True, label='Exp(3)')

#~ plt.hist(h_calls_profile, bins=500, histtype='stepfilled', color='r', label='Calls intensity')
#~ plt.hist(numpy.random.exponential(scale=5, size=100), bins=100, histtype='stepfilled', normed=True, label='Exp(5)')
#~ plt.hist(numpy.random.exponential(scale=10, size=100), bins=100, histtype='stepfilled', normed=True, label='Exp(10)')
#~ plt.hist(numpy.random.exponential(scale=50, size=100), bins=100, histtype='stepfilled', normed=True, label='Exp(50)')
#~ plt.hist(h_dialing_profile, bins=100, histtype='stepfilled', normed=True, color='r', alpha=0.5, label='Dialing')
plt.title("Distribution of Call Duration and Dialing Time")
plt.xlabel("Time (sec)")
#~ plt.ylabel("Probability")
plt.ylabel("Calls N")
plt.legend()
plt.show()
