#!/usr/bin/env python
# coding=utf-8

"""
Wrapper around ``ffprobe`` to read the properties of an audio file.
"""

import os
import re
import subprocess

import aeneas.globalconstants as gc
import aeneas.globalfunctions as gf
from aeneas.logger import Logger

__author__ = "Alberto Pettarin"
__copyright__ = """
    Copyright 2012-2013, Alberto Pettarin (www.albertopettarin.it)
    Copyright 2013-2015, ReadBeyond Srl (www.readbeyond.it)
    """
__license__ = "GNU AGPL v3"
__version__ = "1.0.3"
__email__ = "aeneas@readbeyond.it"
__status__ = "Production"

class FFPROBEWrapper(object):
    """
    Wrapper around ``ffprobe`` to read the properties of an audio file.

    It will perform a call like::

        $ ffprobe -select_streams a -show_streams /path/to/audio/file.mp3

    and it will parse the first ``[STREAM]`` element returned::

            [STREAM]
            index=0
            codec_name=mp3
            codec_long_name=MP3 (MPEG audio layer 3)
            profile=unknown
            codec_type=audio
            codec_time_base=1/44100
            codec_tag_string=[0][0][0][0]
            codec_tag=0x0000
            sample_fmt=s16p
            sample_rate=44100
            channels=1
            channel_layout=mono
            bits_per_sample=0
            id=N/A
            r_frame_rate=0/0
            avg_frame_rate=0/0
            time_base=1/14112000
            start_pts=0
            start_time=0.000000
            duration_ts=1545083190
            duration=109.487188
            bit_rate=128000
            max_bit_rate=N/A
            bits_per_raw_sample=N/A
            nb_frames=N/A
            nb_read_frames=N/A
            nb_read_packets=N/A
            DISPOSITION:default=0
            DISPOSITION:dub=0
            DISPOSITION:original=0
            DISPOSITION:comment=0
            DISPOSITION:lyrics=0
            DISPOSITION:karaoke=0
            DISPOSITION:forced=0
            DISPOSITION:hearing_impaired=0
            DISPOSITION:visual_impaired=0
            DISPOSITION:clean_effects=0
            DISPOSITION:attached_pic=0
            [/STREAM]

    :param logger: the logger object
    :type  logger: :class:`aeneas.logger.Logger`
    """

    FFPROBE_PARAMETERS = [
        "-select_streams",
        "a",
        "-show_streams"
    ]
    """ ``ffprobe`` parameters """

    STDERR_DURATION_REGEX = r"Duration: ([0-9]*):([0-9]*):([0-9]*)\.([0-9]*)"
    """ Regex to match ``ffprobe`` stderr duration values """

    STDOUT_BEGIN_STREAM = "[STREAM]"
    """ ``ffprobe`` stdout begin stream tag """

    STDOUT_CHANNELS = "channels"
    """ ``ffprobe`` stdout channels keyword """

    STDOUT_CODEC_NAME = "codec_name"
    """ ``ffprobe`` stdout codec name (format) keyword """

    STDOUT_END_STREAM = "[/STREAM]"
    """ ``ffprobe`` stdout end stream tag """

    STDOUT_DURATION = "duration"
    """ ``ffprobe`` stdout duration keyword """

    STDOUT_SAMPLE_RATE = "sample_rate"
    """ ``ffprobe`` stdout sample rate keyword """

    TAG = "FFPROBEWrapper"

    def __init__(self, logger=None):
        self.logger = logger
        if logger == None:
            self.logger = Logger()

    def _log(self, message, severity=Logger.DEBUG):
        self.logger.log(message, severity, self.TAG)

    def read_properties(self, audio_file_path):
        """
        Read the properties of an audio file
        and return them as a dictionary.

        Example: ::

            d["index"]=0
            d["codec_name"]=mp3
            d["codec_long_name"]=MP3 (MPEG audio layer 3)
            d["profile"]=unknown
            d["codec_type"]=audio
            d["codec_time_base"]=1/44100
            d["codec_tag_string"]=[0][0][0][0]
            d["codec_tag"]=0x0000
            d["sample_fmt"]=s16p
            d["sample_rate"]=44100
            d["channels"]=1
            d["channel_layout"]=mono
            d["bits_per_sample"]=0
            d["id"]=N/A
            d["r_frame_rate"]=0/0
            d["avg_frame_rate"]=0/0
            d["time_base"]=1/14112000
            d["start_pts"]=0
            d["start_time"]=0.000000
            d["duration_ts"]=1545083190
            d["duration"]=109.487188
            d["bit_rate"]=128000
            d["max_bit_rate"]=N/A
            d["bits_per_raw_sample"]=N/A
            d["nb_frames"]=N/A
            d["nb_read_frames"]=N/A
            d["nb_read_packets"]=N/A
            d["DISPOSITION:default"]=0
            d["DISPOSITION:dub"]=0
            d["DISPOSITION:original"]=0
            d["DISPOSITION:comment"]=0
            d["DISPOSITION:lyrics"]=0
            d["DISPOSITION:karaoke"]=0
            d["DISPOSITION:forced"]=0
            d["DISPOSITION:hearing_impaired"]=0
            d["DISPOSITION:visual_impaired"]=0
            d["DISPOSITION:clean_effects"]=0
            d["DISPOSITION:attached_pic"]=0

        :param audio_file_path: the path of the audio file to analyze
        :type  audio_file_path: string (path)
        :rtype: dict
        """

        # test if we can read the file at audio_file_path
        if not os.path.isfile(audio_file_path):
            msg = "File '%s' cannot be read" % audio_file_path
            self._log(msg, Logger.CRITICAL)
            raise OSError(msg)

        # call ffprobe
        arguments = []
        arguments += [gc.FFPROBE_PATH]
        arguments += self.FFPROBE_PARAMETERS
        arguments += [audio_file_path]
        self._log("Calling with arguments '%s'" % str(arguments))
        proc = subprocess.Popen(
            arguments,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE)
        (stdoutdata, stderrdata) = proc.communicate()
        proc.stdout.close()
        proc.stdin.close()
        proc.stderr.close()
        self._log("Call completed")

        # if no output, raise error
        if (stdoutdata == None) or (len(stderrdata) == 0):
            msg = "No output for '%s'" % audio_file_path
            self._log(msg, Logger.CRITICAL)
            raise Exception(msg)

        # dictionary for the results
        results = dict()

        # scan the first audio stream the ffprobe stdout output
        # TODO: more robust parsing 
        # TODO: deal with multiple audio streams
        for line in stdoutdata.splitlines():
            if line == self.STDOUT_END_STREAM:
                self._log("Reached end of the stream")
                break
            elif len(line.split("=")) == 2:
                key, value = line.split("=")
                results[key] = value
                self._log("Found property '%s'='%s'" % (key, value))

        # convert duration to float
        results[self.STDOUT_DURATION] = gf.safe_float(
            results[self.STDOUT_DURATION],
            None
        )

        try:
            # if audio_length is still None, scan ffprobe stderr output
            if results[self.STDOUT_DURATION] == None:
                pattern = re.compile(self.STDERR_DURATION_REGEX)
                for line in stderrdata.splitlines():
                    match = pattern.search(line)
                    if match != None:
                        self._log("Found matching line '%s'" % line)
                        v_h = int(match.group(1))
                        v_m = int(match.group(2))
                        v_s = int(match.group(3))
                        v_f = float("0." + match.group(4))
                        v_length = v_h * 3600 + v_m * 60 + v_s + v_f
                        results[self.STDOUT_DURATION] = v_length
                        self._log("Extracted duration '%f'" % v_length)
                        break
        except ValueError:
            self._log("ValueError exception")
        except TypeError:
            self._log("TypeError exception")

        # return dictionary
        self.logger.log("Returning dict", Logger.DEBUG, self.TAG)
        return results



