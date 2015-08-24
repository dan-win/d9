import dctr as dialercontrol

env = dialercontrol.PIEnvironment().\
                extendfrom(\
                    dialercontrol.CLIEnvironment()\
                )
print dialercontrol.PIController(env).predict_outgoing_calls()


