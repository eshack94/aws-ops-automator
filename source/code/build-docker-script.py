######################################################################################################################
#  Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance        #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://aws.amazon.com/asl/                                                                                    #
#                                                                                                                    #
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################
import sys

import boto3

FIVE_YEARS = 5 * 365 * 24 * 3600


def get_signed_url(bucket, key):
    s3 = boto3.client("s3")

    params = {
        "Bucket": bucket,
        "Key": key
    }

    return s3.generate_presigned_url("get_object", Params=params, ExpiresIn=FIVE_YEARS, HttpMethod="GET")


def build_script(script, bucket, version, prefix):
    ecs_runner_script_url = get_signed_url(bucket, prefix + "ecs/ops-automator-ecs-runner.py")
    docker_file_url = get_signed_url(bucket, prefix + "ecs/Dockerfile")

    with open(script, mode="rt") as f:
        return "".join(f.readlines()) \
            .replace("%ecs_runner_script%", ecs_runner_script_url) \
            .replace("%docker_file%", docker_file_url) \
            .replace("%version%", version)


if __name__ == "__main__":
    try:
        print(build_script(script=sys.argv[1], bucket=sys.argv[2], version=sys.argv[3],
                           prefix=sys.argv[4] if len(sys.argv) > 3 else ""))
    except Exception as ex:
        print(ex)
        exit(1)
