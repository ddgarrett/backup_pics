
"""
    Backup Pictures (BP) Function Class
    
    Superclass of all BP Functions
    
"""

class BpFunction:
    def __init__(self, parms):
        self._parms   = parms

    def run(self):
        """ Run the function with the given parameters.
            This method should be overridden by subclasses.
        """
        raise NotImplementedError("Subclasses must implement this method.") 
    
    def get_parms(self):
        """ Return the parameters for this function. """
        return self._parms
    