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

import os
import time
from datetime import datetime

import boto3

from boto_retry import get_client_with_retries

LOG_FORMAT = "{:0>4d}-{:0>2d}-{:0>2d} - {:0>2d}:{:0>2d}:{:0>2d}.{:0>3s} - {:7s} : {}"

ENV_LOG_GROUP = "LOG_GROUP"
ENV_SNS_TOPIC = "SNS_TOPIC"

LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_DEBUG = "DEBUG"

LOG_MAX_BATCH_SIZE = 1048576
LOG_ENTRY_ADDITIONAL = 26


class Logger:
    """
    Wrapper class for CloudWatch logging with buffering and helper methods
    """

    def __init__(self, logstream, context, loggroup=None, buffersize=10, debug=False):

        def get_loggroup(lambda_context):
            group = os.getenv(ENV_LOG_GROUP, None)
            if group is None:
                if lambda_context is None:
                    return None
                group = lambda_context.log_group_name
            return group

        def create_stream_if_not_exists():

            client = boto3.client("logs")
            resp = client.describe_log_streams(logGroupName=self._loggroup, logStreamNamePrefix=self._logstream)
            if len(resp.get("logStreams", [])) == 0:
                client.create_log_stream(logGroupName=self._loggroup, logStreamName=self._logstream)

        self._logstream = logstream
        self._buffer_size = min(buffersize, 10000)
        self._context = context
        self._buffer = []
        self._debug = debug
        self._cached_size = 0
        self._loggroup = loggroup if loggroup is not None else get_loggroup(self._context)
        if self._loggroup:
            create_stream_if_not_exists()

        self._sns = None

    def __enter__(self):
        """
        Returns itself as the managed resource.
        :return:
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Writes all cached action items to dynamodb table when going out of scope
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        self.flush()

    def _emit(self, level, msg, *args):

        s = msg if len(args) == 0 else msg.format(*args)
        t = time.time()
        dt = datetime.fromtimestamp(t)
        s = LOG_FORMAT.format(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                              dt.second, str(dt.microsecond)[0:3], level, s)

        if self._cached_size + (len(s) + LOG_ENTRY_ADDITIONAL) > LOG_MAX_BATCH_SIZE:
            self.flush()

        self._cached_size += len(s) + LOG_ENTRY_ADDITIONAL

        if self._context is not None:
            self._buffer.append((long(t * 1000), s))
        else:
            print("> " + s)

        if len(self._buffer) >= self._buffer_size:
            self.flush()

        return s

    @property
    def debug_enabled(self):
        """
        Return debug on/off switch
        :return: debug on/of
        """
        return self._debug

    @property
    def sns(self):
        if self._sns is None:
            self._sns = get_client_with_retries("sns", ["publish"], context=self._context)
        return self._sns

    @debug_enabled.setter
    def debug_enabled(self, value):
        """
        Sets debug switch
        :param value: True to enable debugging, False to disable
        :return: 
        """
        self._debug = value

    def publish_to_sns(self, level, msg):
        """
        Publis message to sns topic
        :param msg: 
        :param level: 
        :return: 
        """
        sns_arn = os.getenv(ENV_SNS_TOPIC, None)
        if sns_arn is not None:
            message = "Loggroup: {}\nLogstream {}\n{} : {}".format(self._loggroup, self._logstream, level, msg)
            self.sns.publish_with_retries(TopicArn=sns_arn, Message=message)

    def info(self, msg, *args):
        """
        Logs informational message
        :param msg: Message format string
        :param args: Message parameters
        :return: 
        """
        self._emit(LOG_LEVEL_INFO, msg, *args)

    def error(self, msg, *args):
        """
        Logs error message
        :param msg: Error message format string
        :param args: parameters
        :return: 
        """
        s = self._emit(LOG_LEVEL_ERROR, msg, *args)
        self.publish_to_sns("Error", s)

    def warning(self, msg, *args):
        """
        Logs warning message
        :param msg: Warning message format string
        :param args: parameters
        :return: 
        """
        s = self._emit(LOG_LEVEL_WARNING, msg, *args)
        self.publish_to_sns("Warning", s)

    def debug(self, msg, *args):
        """
        Conditionally logs debug message, does not log if debugging is disabled
        :param msg: Debug message format string
        :param args: parameters
        :return: 
        """
        if self._debug:
            self._emit(LOG_LEVEL_DEBUG, msg, *args)

    def clear(self):
        """
        Clear all buffered error messages
        :return: 
        """
        self._buffer = []

    @property
    def _client(self):
        client = get_client_with_retries("logs", ["describe_log_streams", "put_log_events"], context=self._context)
        return client

    def flush(self):
        """
        Writes all buffered messages to CloudWatch Stream
        :return: 
        """

        if len(self._buffer) == 0:
            return

        put_event_args = {
            "logGroupName": self._loggroup,
            "logStreamName": self._logstream,
            "logEvents": [{"timestamp": r[0], "message": r[1]} for r in self._buffer]
        }

        client = self._client

        try:
            next_log_token = None

            resp = client.describe_log_streams_with_retries(logGroupName=self._loggroup, logStreamNamePrefix=self._logstream)
            if "logStreams" in resp and len(resp["logStreams"]) > 0:
                next_log_token = resp["logStreams"][0].get("uploadSequenceToken")

            if next_log_token is not None:
                put_event_args["sequenceToken"] = next_log_token

            client.put_log_events_with_retries(**put_event_args)
            self._buffer = []
            self._cached_size = 0
            return
        except Exception as ex:
            print("Error writing to logstream {} ({})".format(self._logstream, str(ex)))
            for entry in self._buffer:
                print (entry)