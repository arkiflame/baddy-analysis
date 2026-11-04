"""Milestone 2 tooling: turning our own footage into ShuttleSet-style stroke data.

* calibrate_court : click the four court corners -> homography row (ShuttleSet format)
* label_video     : step through a video, click the shuttle, mark hits/shots -> stroke CSV
* tracknet        : thin wrapper around TrackNetV3 (MIT) inference
"""
