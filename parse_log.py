# fix division problem:
from __future__ import division

import csv

import math
import random
import itertools

import statistics

import sys
try:
    import matplotlib.pyplot as plt
    import numpy
except ImportError:
    print "Requires matplotlib and numpy modules!"
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


#~ class PoissonProfile(NumSequence):
    #~ def __init__(self, xmin, xmax, step, k=1, lam=1):
        #~ NumSequence.__init__(self)
        #~ self.k = k
        #~ self.lam = lam
    
    #~ def update(self, v=None):
        #~ v = numpy.random.poisson(float(self.lam))
        #~ Profile.update(self, v)

#~ class ExpovarianteProfile(NumSequence):
    #~ def __init__(self, xmin, xmax, step, k=1, lam=1):
        #~ Profile.__init__(self, xmin, xmax, step)
        #~ self.k = k
        #~ self.lam = lam
    
    #~ def update(self, v=None):
        #~ v = random.expovariate(float(self.lam))
        #~ Profile.update(self, v)            

#~ class LognormalProfile(Profile):
    #~ def __init__(self, xmin, xmax, step, mean, sigma):
        #~ Profile.__init__(self, xmin, xmax, step)
        #~ self.logmean = mean
        #~ self.logsigma = sigma
        #~ s = numpy.random.lognormal(mean=self.logmean, sigma=self.logsigma, size=100000)
        #~ for v in s:
            #~ Profile.update(self, v)
    



def expovariate(k, lambd, size):
    buff = [] 
    count = 0
    while count < size:
        buff.append(k * random.expovariate(lambd))
        count += 1
    return buff

def main():
    d_agents = {}

    t_uptime = 0
    t_service_time = 0
    n_calls = 0
    n_answered_calls = 0
    weighted_average_call_duration = 0

    vmin = 0
    vmax = 2000
    quantum = 2
    c_duration = statistics.NumSet(label='Call duration')
    c10_duration = statistics.NumSet(label='Call duration (calls longer than 10 sec)')
    c_calls_distribution = statistics.NumXY(label='Calls distribution by day time')
    c_dialing_profile = statistics.NumSet(label='Dialing duration')
    #~ c_dmodel_poisson = PoissonProfile(vmin, vmax, quantum, k = 0.5, lam = 1)
    #~ c_dmodel_expovariate = ExpovarianteProfile(vmin, vmax, quantum, k = 0.5, lam = 1)
    #~ c_dmodel_lognormal = LognormalProfile(vmin, vmax, quantum, mean=38, sigma = 3600)

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
            c_calls_distribution.append(call_time, 1)
            talk_time = line['talk_time'] = timefromdatestr(line['talk_time']) 
            
            if talk_time is not None and  call_time is not None:
                dialing_time = line['dialing_time'] = talk_time - call_time
                c_dialing_profile.append(dialing_time)
            else:
                dialing_time = line['dialing_time'] = None
            
            call_duration = line['call_duration'] = timefromtimestr(line['call_duration'])
            #~ if call_duration and line["classification"] != 'Voicemail':
            if call_duration:
                c_duration.append(call_duration)
            if call_duration and call_duration > 10:
                n_answered_calls += 1
                t_service_time += call_duration
                c10_duration.append(call_duration)
                #~ c_dmodel_poisson.update()
                #~ c_dmodel_expovariate.update()
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
        
    h_calls_profile = statistics.Histogram(label='Histogram: call duration', source=c_duration, bins=20)
    h_calls10_profile = statistics.Histogram(label='Histogram: call duration (call duration > 10 sec)', source=c10_duration, bins=20)
    h_dialing_profile = statistics.Histogram(label='Histogram: duration of dialing', source=c_dialing_profile)

    print "Results are below, see also on the popup plot window"
    print c_duration
    print c10_duration
    print c_calls_distribution
    
    print h_dialing_profile
    print h_calls10_profile
    print h_calls_profile
    
    c_duration.store('c_duration.dat')
    c10_duration.store('c10_duration.dat')

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

    
    #~ print 'Poisson model: ', c_dmodel_poisson
    #~ print 'Expovariante model: ', c_dmodel_expovariate
    #~ print 'Lognormal model: ', c_dmodel_lognormal

    #~ h_duration_profile = cuttail(h_duration_profile, 25)
    #~ p0 = cuttail(poisson(k=25, lam=2, size=1000), 25)
    #~ e = cuttail(expovariate(average_call_duration, answered_call_rate, 1000), 25)
    #~ e1 = cuttail(numpy.random.exponential(scale=0.5, size=1000), 25)
    #~ e2 = cuttail(numpy.random.exponential(scale=1, size=1000), 25)
    #~ e3 = cuttail(numpy.random.exponential(scale=2, size=1000), 25)

    #~ plt.hist(h_duration_profile, bins=1000, histtype='step', color='b', rwidth=20, label='Duration')
    #~ plt.hist(p0, bins=100, histtype='step', color='g', normed=True, rwidth=20, label='Poisson(2)')

    plt.plot(*h_calls_profile(), label = h_calls_profile.label)
    plt.plot(*h_calls10_profile(), label = h_calls10_profile.label)
    
    #~ plt.plot(*c_dmodel_poisson(), label = 'c_dmodel_poisson')
    #~ plt.plot(*c_dmodel_expovariate(), label = 'c_dmodel_expovariate')
    #~ plt.plot(*c_dmodel_lognormal(), label = 'c_dmodel_lognormal')
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
    
if __name__ == '__main__':
    main()
    #~ import doctest
    #~ doctest.testmod()
    
    #~ p = NumSet()
    #~ p.fromlist([0,10,10,10,10,20,20, 30, 40])
    #~ p.y
    
    #~ h = Histogram(source=p, bins=3)
    #~ print h
    