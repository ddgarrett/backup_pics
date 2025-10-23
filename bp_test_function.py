

'''
    BP Test Function
'''

from bp_function import BpFunction

class MyFunction(BpFunction):
    def __init__(self, parms):
        super().__init__(parms)

    def run(self):
        print("MyFunction run called with parms:", self.get_parms())