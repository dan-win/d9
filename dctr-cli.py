import dctr as dialercontrol

env = dialercontrol.PIEnvironment().\
                extendfrom(\
                    dialercontrol.CLIEnvironment()\
                )
print '\n'.join(env.dump())
print '---'
print dialercontrol.PIController(env).predict_outgoing_calls(debug=True)


