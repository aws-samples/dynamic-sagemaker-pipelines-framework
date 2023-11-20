import argparse
from pipeline.pipeline_service import PipelineService

parser = argparse.ArgumentParser()
parser.add_argument("--runMode", type=str, default="train", help="Should be either 'train' or 'inference")
args, _ = parser.parse_known_args()
if args.runMode in ["train", "inference"]:
    run_mode = args.runMode
else:
    raise Exception("runMode argument invalid.Must be either train or inference")

pipeline = PipelineService(run_mode)
pipeline.execute_pipeline()