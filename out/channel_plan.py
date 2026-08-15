"""Channel plan recovered from a radio dump by tools/dump_to_plan.py.

Feed to tools/build_channels.py. Channel numbers in comments are the
1-based numbers the radio's display shows.
"""

CHANNELS = []

def at(n, rec):
    """Place a record at 1-based display channel n, padding gaps with None.

    Gaps are intentional: the knob skips unprogrammed slots entirely, so
    leaving space between groups costs nothing and keeps each group's
    numbering stable when one is edited.
    """
    while len(CHANNELS) < n - 1:
        CHANNELS.append(None)
    if len(CHANNELS) == n - 1:
        CHANNELS.append(rec)
    else:
        CHANNELS[n - 1] = rec

at(1, make(462562500, name="GMRS 1"))  # 462.5625
at(2, make(462587500, name="GMRS 2"))  # 462.5875
at(3, make(462612500, name="GMRS 3"))  # 462.6125
at(4, make(462637500, name="GMRS 4"))  # 462.6375
at(5, make(462662500, name="GMRS 5"))  # 462.6625
at(6, make(462687500, name="GMRS 6"))  # 462.6875
at(7, make(462712500, name="GMRS 7"))  # 462.7125
at(8, make(467562500, name="GMRS 8"))  # 467.5625
at(9, make(467587500, name="GMRS 9"))  # 467.5875
at(10, make(467612500, name="GMRS 10"))  # 467.6125
at(11, make(467637500, name="GMRS 11"))  # 467.6375
at(12, make(467662500, name="GMRS 12"))  # 467.6625
at(13, make(467687500, name="GMRS 13"))  # 467.6875
at(14, make(467712500, name="GMRS 14"))  # 467.7125
at(15, make(462550000, name="GMRS 15"))  # 462.5500
at(16, make(462575000, name="GMRS 16"))  # 462.5750
at(17, make(462600000, name="GMRS 17"))  # 462.6000
at(18, make(462625000, name="GMRS 18"))  # 462.6250
at(19, make(462650000, name="GMRS 19"))  # 462.6500
at(20, make(462675000, name="GMRS 20"))  # 462.6750
at(21, make(462700000, name="GMRS 21"))  # 462.7000
at(22, make(462725000, name="GMRS 22"))  # 462.7250
# ---- gap: 42 unprogrammed slots ----
at(65, make(462700000, tx=467700000, txtone="136.5", name="ROCKHAM"))  # 462.7000 / tx 467.7000 (+5.0)  tone 136.5
at(66, make(462625000, tx=467625000, txtone="D073N", name="BOGUS"))  # 462.6250 / tx 467.6250 (+5.0)  tone D073N
at(67, make(462550000, tx=467550000, txtone="D664N", name="SEEK0"))  # 462.5500 / tx 467.5500 (+5.0)  tone D664N
at(68, make(462675000, tx=467675000, txtone="D205N", name="TV675"))  # 462.6750 / tx 467.6750 (+5.0)  tone D205N
at(69, make(462575000, tx=467575000, txtone="100.0", name="ADHOC575"))  # 462.5750 / tx 467.5750 (+5.0)  tone 100.0
at(70, make(462600000, tx=467600000, txtone="67.0", name="CALDWEL"))  # 462.6000 / tx 467.6000 (+5.0)  tone 67.0
at(71, make(462725000, tx=467725000, txtone="103.5", name="STAR"))  # 462.7250 / tx 467.7250 (+5.0)  tone 103.5
at(72, make(462700000, tx=467700000, txtone="250.3", name="SQUAWBT"))  # 462.7000 / tx 467.7000 (+5.0)  tone 250.3
at(73, make(462650000, tx=467650000, txtone="71.9", name="HOMEDL1"))  # 462.6500 / tx 467.6500 (+5.0)  tone 71.9
at(74, make(462725000, tx=467725000, txtone="141.3", name="HOMEDL2"))  # 462.7250 / tx 467.7250 (+5.0)  tone 141.3
at(75, make(462625000, tx=467625000, txtone="141.3", name="GRAVEYRD"))  # 462.6250 / tx 467.6250 (+5.0)  tone 141.3
at(76, make(462600000, tx=467600000, txtone="141.3", name="JAKE"))  # 462.6000 / tx 467.6000 (+5.0)  tone 141.3
at(77, make(462650000, tx=467650000, txtone="127.3", name="GV650"))  # 462.6500 / tx 467.6500 (+5.0)  tone 127.3
at(78, make(462675000, tx=467675000, txtone="141.3", name="MTNHOME"))  # 462.6750 / tx 467.6750 (+5.0)  tone 141.3
at(79, make(462700000, tx=467700000, txtone="123.0", name="CRB700"))  # 462.7000 / tx 467.7000 (+5.0)  tone 123.0
at(80, make(462550000, tx=467550000, txtone="136.5", name="TWINFALL"))  # 462.5500 / tx 467.5500 (+5.0)  tone 136.5
at(81, make(462575000, tx=467575000, txtone="173.8", name="BUHL"))  # 462.5750 / tx 467.5750 (+5.0)  tone 173.8
at(82, make(462625000, tx=467625000, txtone="97.4", name="SODASPR"))  # 462.6250 / tx 467.6250 (+5.0)  tone 97.4
at(83, make(462650000, tx=467650000, txtone="141.3", name="BLACKFT"))  # 462.6500 / tx 467.6500 (+5.0)  tone 141.3
at(84, make(462650000, tx=467650000, txtone="136.5", name="ISLNDPRK"))  # 462.6500 / tx 467.6500 (+5.0)  tone 136.5
# ---- gap: 16 unprogrammed slots ----
at(101, make(162400000, rx_only=True, name="ZONETEST"))  # 162.4000 rx-only
# ---- gap: 27 unprogrammed slots ----
at(129, make(462675000, tx=467675000, txtone="141.3", name="SALINA"))  # 462.6750 / tx 467.6750 (+5.0)  tone 141.3
at(130, make(462650000, tx=467650000, txtone="131.8", name="REDMOND"))  # 462.6500 / tx 467.6500 (+5.0)  tone 131.8
at(131, make(462700000, tx=467700000, txtone="D223N", name="OAKCITY"))  # 462.7000 / tx 467.7000 (+5.0)  tone D223N
at(132, make(462700000, tx=467700000, txtone="118.8", name="MONTICEL"))  # 462.7000 / tx 467.7000 (+5.0)  tone 118.8
at(133, make(462675000, tx=467675000, txtone="141.3", name="STGEORGE"))  # 462.6750 / tx 467.6750 (+5.0)  tone 141.3
at(134, make(462625000, tx=467625000, txtone="141.3", name="KAMAS"))  # 462.6250 / tx 467.6250 (+5.0)  tone 141.3
at(135, make(462650000, tx=467650000, txtone="D712N", name="OAKLEY"))  # 462.6500 / tx 467.6500 (+5.0)  tone D712N
at(136, make(462575000, tx=467575000, txtone="136.5", name="PARKCITY"))  # 462.5750 / tx 467.5750 (+5.0)  tone 136.5
at(137, make(462600000, tx=467600000, txtone="179.9", name="SLCEAST"))  # 462.6000 / tx 467.6000 (+5.0)  tone 179.9
at(138, make(462550000, tx=467550000, txtone="146.2", name="SLCWEST1"))  # 462.5500 / tx 467.5500 (+5.0)  tone 146.2
at(139, make(462575000, tx=467575000, txtone="D371N", name="SLCWEST2"))  # 462.5750 / tx 467.5750 (+5.0)  tone D371N
at(140, make(462650000, tx=467650000, txtone="131.8", name="SARATOGA"))  # 462.6500 / tx 467.6500 (+5.0)  tone 131.8
at(141, make(462675000, tx=467675000, txtone="D114N", name="PLYMOUTH"))  # 462.6750 / tx 467.6750 (+5.0)  tone D114N
# ---- gap: 51 unprogrammed slots ----
at(193, make(462700000, tx=467700000, txtone="136.5", name="RENO700"))  # 462.7000 / tx 467.7000 (+5.0)  tone 136.5
at(194, make(462575000, tx=467575000, txtone="110.9", name="RENO575"))  # 462.5750 / tx 467.5750 (+5.0)  tone 110.9
at(195, make(462550000, tx=467550000, txtone="141.3", name="CARSON550"))  # 462.5500 / tx 467.5500 (+5.0)  tone 141.3
at(196, make(462675000, tx=467675000, txtone="141.3", name="MINDEN675"))  # 462.6750 / tx 467.6750 (+5.0)  tone 141.3
at(197, make(462625000, tx=467625000, txtone="250.3", name="MINDEN625"))  # 462.6250 / tx 467.6250 (+5.0)  tone 250.3
at(198, make(462550000, tx=467550000, txtone="156.7", name="PINENUT"))  # 462.5500 / tx 467.5500 (+5.0)  tone 156.7
at(199, make(462625000, tx=467625000, txtone="162.2", name="RACHEL"))  # 462.6250 / tx 467.6250 (+5.0)  tone 162.2
# ---- gap: 57 unprogrammed slots ----
at(257, make(162400000, rx_only=True, name="NOAA 1"))  # 162.4000 rx-only
at(258, make(162425000, rx_only=True, name="NOAA 2"))  # 162.4250 rx-only
at(259, make(162450000, rx_only=True, name="NOAA 3"))  # 162.4500 rx-only
at(260, make(162475000, rx_only=True, name="NOAA 4"))  # 162.4750 rx-only
at(261, make(162500000, rx_only=True, name="NOAA 5"))  # 162.5000 rx-only
at(262, make(162525000, rx_only=True, name="NOAA 6"))  # 162.5250 rx-only
at(263, make(162550000, rx_only=True, name="NOAA 7"))  # 162.5500 rx-only
# ---- gap: 57 unprogrammed slots ----
at(321, make(146520000, name="HAMCALL"))  # 146.5200
at(322, make(146760000, tx=146160000, txtone="88.5", name="MOAB146"))  # 146.7600 / tx 146.1600 (-0.6)  tone 88.5
at(323, make(146900000, tx=146300000, txtone="88.5", name="MOAB147"))  # 146.9000 / tx 146.3000 (-0.6)  tone 88.5
at(324, make(447650000, tx=442650000, txtone="151.4", name="MOABUHF"))  # 447.6500 / tx 442.6500 (-5.0)  tone 151.4
at(325, make(146610000, tx=146010000, txtone="88.5", name="MONTI146"))  # 146.6100 / tx 146.0100 (-0.6)  tone 88.5
at(326, make(447100000, tx=442100000, txtone="107.2", name="MONTIUHF"))  # 447.1000 / tx 442.1000 (-5.0)  tone 107.2
at(327, make(146620000, tx=146020000, txtone="100.0", name="SNOWBNK"))  # 146.6200 / tx 146.0200 (-0.6)  tone 100.0
at(328, make(146660000, tx=146060000, txtone="100.0", name="SNOWBNK2"))  # 146.6600 / tx 146.0600 (-0.6)  tone 100.0
at(329, make(147020000, tx=147620000, txtone="100.0", name="NOBIZMTN"))  # 147.0200 / tx 147.6200 (+0.6)  tone 100.0
at(330, make(146700000, tx=146100000, txtone="100.0", name="SQUAWB2"))  # 146.7000 / tx 146.1000 (-0.6)  tone 100.0
at(331, make(146740000, tx=146140000, txtone="100.0", name="SQUAWB3"))  # 146.7400 / tx 146.1400 (-0.6)  tone 100.0
at(332, make(442750000, tx=447750000, txtone="100.0", name="SQUAWUHF"))  # 442.7500 / tx 447.7500 (+5.0)  tone 100.0
at(333, make(147150000, tx=147750000, txtone="123.0", name="MTROSE"))  # 147.1500 / tx 147.7500 (+0.6)  tone 123.0
at(334, make(146760000, tx=146160000, txtone="123.0", name="PEAVINE"))  # 146.7600 / tx 146.1600 (-0.6)  tone 123.0
# ---- gap: 50 unprogrammed slots ----
at(385, make(462675000, name="GMRS 20"))  # 462.6750
at(386, make(462675000, txtone="141.3", name="EMERG20"))  # 462.6750  tone 141.3
at(387, make(462675000, tx=467675000, txtone="141.3", name="SSLAKE"))  # 462.6750 / tx 467.6750 (+5.0)  tone 141.3
at(388, make(462625000, tx=467625000, txtone="141.3", name="FARMNGT"))  # 462.6250 / tx 467.6250 (+5.0)  tone 141.3
at(389, make(462600000, tx=467600000, txtone="141.3", name="JUNCTUT"))  # 462.6000 / tx 467.6000 (+5.0)  tone 141.3
at(390, make(146840000, rx_only=True, name="SHAFER1"))  # 146.8400 rx-only
at(391, make(146940000, rx_only=True, name="SHAFER2"))  # 146.9400 rx-only

ZONES = {
    0: "ZoneOne",
    1: "ZoneTwo",
    2: "ZoneThree",
    3: "ZoneFour",
    4: "ZoneFive",
    5: "ZoneSix",
    6: "ZoneSeven",
    7: "ZoneEight",
    8: "ZoneNine",
    9: "ZoneTen",
}

