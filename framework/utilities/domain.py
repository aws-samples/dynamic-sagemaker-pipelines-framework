# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import glob
from typing import Any
import yaml

class Conf:
    """
    Class to Read Framework config and all complementary app Conf files.
    """
    def __init__(self):
        self.path = "framework/conf/conf.yaml"
    
    def load_conf(self):
        """
        Method to load and merge all Conf files
        """
        base_conf, conf_path = self._get_framework_conf()
        base_conf["conf"]["models"]["modelContainer"] = {}

        modelDomainConfigFilePath= base_conf["conf"]["models"]["modelDomainConfigFilePath"]
        yaml_files = glob.glob(f"{self._get_parent_dir()}/{modelDomainConfigFilePath}", recursive=True)

        for file_path in yaml_files:
            if file_path.startswith(conf_path):
                continue
            model_conf = self._read_yaml_file(file_path)
            # Insert Models Attibutes into Framework attribute in a runtime
            for key, value in model_conf["conf"]["models"]["modelContainer"].items():
                base_conf["conf"]["models"]["modelContainer"].setdefault(key, {}).update(value)

            # Insert sagemakerPipeline section as a primary key
            for key, value in model_conf["conf"].items():
                if key == "sagemakerPipeline":
                    base_conf["conf"]["sagemakerPipeline"] = {}
                    base_conf["conf"]["sagemakerPipeline"].update(value)

        print(DotDict(base_conf).get("conf"))
        return DotDict(base_conf).get("conf")

    def _get_framework_conf(self):
        """
        Load the Framework Conf file
        """
        path = self.path
        root = self._get_parent_dir()
        conf_path = os.path.join(root, path)

        with open(conf_path, "r") as f:
            conf = yaml.safe_load(f)
        return conf, conf_path
    
    def _get_parent_dir(self):
        """
        Get the parent directory from where the framework is been executed
        """
        subdirectory = "framework"
        current_directory = os.getcwd()

        substring = str(current_directory).split("/")
        parent_dir = [path for path in substring if path != subdirectory]
        
        return "/".join(parent_dir)
    
    def _read_yaml_file(self, file_path: str):
        """
        Read YAML file

        Args:
        ----------
        - file_path (str): Conf file path

        """
        with open(file_path, "r") as f:
            return yaml.safe_load(f)
        
class DotDict(dict):
    """
    A dictionary subclass that enables dot notation for nested access
    """
    def __getattr__(self, key: str) -> "DotDict":
        """
        Retreive the value of a nested key using dot notation.

        Args:
        ----------
        - key (str): Yhe nested key in dot notation

        Returns:
        ----------
        - The value of the nested key, wrapped in a "DotDict" if the value is a dictionary.

        Raises:
        ----------
        - AttributeError: If the nested key is not found.
        """
        if key in self:
            value = self[key]
            if isinstance(value, dict):
                return DotDict(value)
            return value
        else:
            return DotDict()
        
    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value
        
    def __delattr__(self, key: str) -> None:
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"{self.__class__.__name__} object has no attribute {key}")
        
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Retreive the value of a nested key using dot notation

         Args:
        ----------
        - key (str): The nested key in dot notation.
        - default (Any): The default value to return if the nested keyis not found. Default is None

        Returns:
        ----------
        - The value of the nested key if found, or the specified default value if not found.
        """
        keys = key.split(".")
        value = self
        for k in keys:
            value = value.__getattr__(k)
            if not isinstance(value, DotDict):
                break
        return value if value is not None else default
    
    def get(self, key:str, default: Any = None) -> Any:
        """
        Retreive the value of a nested key using dot notation

         Args:
        ----------
        - key (str): The nested key in dot notation.
        - default (Any): The default value to return if the nested keyis not found. Default is None

        Returns:
        ----------
        - The value of the nested key if found, or the specified default value if not found.
        """
        value = self.get_value(key)
        return value if value is not None and value != {} else default
