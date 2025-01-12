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
import calendar

from scheduling.setbuilder import SetBuilder


class MonthSetBuilder(SetBuilder):
    """
    Class for building month sets, 1-12 ans jan-dec
    """

    def __init__(self, wrap=True, ignore_case=True):
        """
        Initializes set builder for month sets
        :param wrap: Set to True to allow wrapping at last month of the year
        :param ignore_case: Set to True to ignore case when mapping month names
        """
        SetBuilder.__init__(self,
                            names=calendar.month_abbr[1:],
                            significant_name_characters=3,
                            offset=1,
                            ignore_case=ignore_case,
                            wrap=wrap)
