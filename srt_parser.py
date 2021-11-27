from dataclasses import dataclass
from datetime import datetime
import re

@dataclass
class SrtRecord:
    frame_start: str
    frame_end: str
    timestamp: str
    frame_count: int
    frame_time: int
    iso: int
    shutter: str
    fnum: int
    ev: int
    ct: int
    color_md: str
    focal_len: int
    latitude: float
    longitude: float
    altitude: float


class SrtParser:

    __srt_regex = """[0-9]+
(?P<frame_start>[0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3}) --> (?P<frame_end>[0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3})
<font size="[0-9]+">FrameCnt: (?P<frame_count>[0-9]+), DiffTime: (?P<frame_time>[0-9]+)ms
(?P<timestamp>[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]+)
\[iso : (?P<iso>[0-9]+)\] \[shutter : (?P<shutter>[0-9]+/[0-9]+\.[0-9]+)\] \[fnum : (?P<fnum>[0-9]+)\] \[ev : (?P<ev>[0-9]+)\] \[ct : (?P<ct>[0-9]+)\] \[color_md : (?P<color_md>[a-zA-Z]+)\] \[focal_len : (?P<focal_len>[0-9]+)\] \[latitude: (?P<latitude>-?[0-9]+\.[0-9]+)\] \[longitude: (?P<longitude>-?[0-9]+\.[0-9]+)\] \[altitude: (?P<altitude>-?[0-9]+\.[0-9]+)\] </font>
"""

    def __init__(self): 
        self.__compiled_regex = re.compile(self.__srt_regex)

    def parse(self, file: str) -> list[SrtRecord]:
        with open(file) as f:
            return self.parse_string(f.read())

    def parse_string(self, string: str) -> list[SrtRecord]:
        for match in self.__compiled_regex.finditer(string):
            record = SrtRecord(
                **match.groupdict()
            )
            yield record

