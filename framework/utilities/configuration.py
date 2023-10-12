import yaml

with open("../../model/config.yaml", "r") as config_file:
    try:
        my_config = yaml.safe_load(config_file)
    except yaml.YAMLError as exc:
        print(exc)
    
model_list = list(my_config["sagemakerPipeline"]["models"].keys())

def get_model_details(config, model_name):
    return config["sagemakerPipeline"]["models"][model_name]

def get_processing_details(model_details):
    return model_details["processing"]

print(get_processing_details(get_model_details(my_config, "example_model_one")))
# print(list(model_list.keys()))