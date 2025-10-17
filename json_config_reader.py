import json

"""
generate a python class reads a .json file to create a dictionary. 
Also allow specification of a "default" dictionary which will be accessed 
if a given property is not found in the .json file
"""
class JsonConfigReader:
    """
    A class to read configuration from a JSON file, with support for default values.
    """
    def __init__(self, json_filepath, default_config=None):
        """
        Initializes the JsonConfigReader.

        Args:
            json_filepath (str): The path to the JSON configuration file.
            default_config (dict, optional): A dictionary of default values.
                                             If a key is not found in the JSON file,
                                             its value will be retrieved from this dictionary.
                                             Defaults to an empty dictionary.
        """
        self.json_filepath = json_filepath
        self.default_config = default_config if default_config is not None else {}
        self._config = self._load_config()

    def _load_config(self):
        """
        Loads the configuration from the JSON file.
        If the file is not found or is invalid JSON, an empty dictionary is returned.
        """
        try:
            with open(self.json_filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: JSON file not found at '{self.json_filepath}'. Using default values.")
            return {}
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in '{self.json_filepath}'. Using default values.")
            return {}

    def get(self, key, default=None):
        """
        Retrieves a value from the loaded configuration.
        If the key is not found in the loaded JSON, it attempts to retrieve it
        from the default_config. If still not found, it returns the provided
        'default' argument, or None if no 'default' is provided.

        Args:
            key (str): The key of the property to retrieve.
            default (any, optional): The value to return if the key is not found
                                     in either the JSON or default configuration.
                                     Defaults to None.

        Returns:
            any: The value associated with the key, or the default value if not found.
        """
        if key in self._config:
            return self._config[key]
        elif key in self.default_config:
            return self.default_config[key]
        else:
            return default

    def __getitem__(self, key):
        """
        Allows dictionary-like access to configuration properties (e.g., config['key']).
        Raises KeyError if the key is not found in either the JSON or default configuration.
        """
        value = self.get(key)
        if value is not None:
            return value
        raise KeyError(f"Key '{key}' not found in JSON or default configuration.")

    def as_dict(self):
        """
        Returns the combined configuration as a dictionary, with JSON values
        overriding default values.
        """
        combined_config = self.default_config.copy()
        combined_config.update(self._config)
        return combined_config