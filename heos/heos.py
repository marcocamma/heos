#! /usr/bin/python3
import socket
import json
import time
import inspect

# PID = Player ID
# SID = Station(?) ID
# SPID = Speaker ID

PID = "AUTO"
IP = "192.168.1.36"
PORT = 1255

TIME_AFTER_SENDING_BEFORE_RECEIVING = 0.1


def parse_json(ret):
    try:
        ret = json.loads(ret)
    except:
        return ret

    if "payload" in ret:
        ret["ANSWER"] = ret["payload"]
    elif "&" in ret["heos"]["message"]:
        status, *ans = ret["heos"]["message"].split("&")
        ans_dict = dict()
        for par in ans:
            key, value = par.split("=")
            ans_dict[key] = value
        ret["ANSWER"] = ans_dict
        ret["STATUS"] = status
    return ret


def parse_what_is_playing(ret):
    media_type = ret["mid"].lower()

    str_repr = None

    if media_type.startswith("cd"):
        track = int(ret["station"].split(" ")[-1])
        str_repr = f" - Listening CD track {track}"
    elif media_type.startswith("http"):
        if "station" in ret:
            str_repr = f" - Listening to Internet Radio : {ret['station']}"
            for key in ("artist", "song"):
                str_repr += f"\n  - {key:8s} : {ret[key]}"
        else:
            str_repr = f" - Listening to Podcast or Song"
            str_repr += f"\n  - date|artist : {ret['artist']}"
            str_repr += f"\n  - song|title  : {ret['song']}"
    elif media_type.startswith("spotify"):
        str_repr = f" - Listening to Spotify"
        for key in ("artist", "song"):
            str_repr += f"\n  - {key:8s} : {ret[key]}"
    elif media_type.startswith("inputs/"):
        input_string = media_type.replace("inputs/", "").replace("_", " ")
        str_repr = f" - Listening to input {input_string}"
    elif media_type == "tuner":
        station = ret["station"]
        station_name = ret["artist"]
        str_repr = f" - Listening to Radio {station}"
        if station_name != "":
            str_repr += " (RDS {station_name})"

    if str_repr is None:
        str_repr = str(ret)

    return str_repr


# TODO examples
# - parse: h.browse("get_music_sources")


class SubMenu:
    def __str__(self):
        options = dir(self)
        options = [o for o in options if not o[:2] == "__"]
        return "Submenu with " + str(options)

    def __repr__(self):
        return self.__str__()

    def _get_childs(self):
        names = dir(self)
        return [n for n in names if not n.startswith("_")]


class HEOS:
    def __init__(self, ip=IP, pid=PID, port=PORT, verbose=False):
        """ Local Music is the tuner, CD, etc. """
        self._ip = ip
        self._port = port
        self._verbose = verbose
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((ip, port))
        self._sock.settimeout(0.2)
        self._query("system", "prettify_json_response", enable="on")
        if pid.lower() == "auto":
            pid = self._query("player", "get_players")[0]["pid"]
        elif isinstance(pid, int):
            pid = self._query("player", "get_players")[pid]["pid"]
        self._pid = pid
        self._SID = None

        self.favorites = SubMenu()
        self.favorites.show = self._show_favorites
        self.favorites.play = self._play_favorite

        self.volume = SubMenu()
        self.volume.get = self._get_volume
        self.volume.set = self._set_volume
        self.volume.up = self._volume_up
        self.volume.down = self._volume_down
        self.volume.mute = self._mute
        self.volume.unmute = self._unmute

        self.play = SubMenu()
        self.play.playing = self._what_is_playing
        self.play.previous = self._play_previous
        self.play.next = self._play_next
        self.play.what = self._play
        self.play.radio = self._radio
        self.play.cd = self._cd
        self.play.optical1 = self._optical1

        self.sources = SubMenu()
        self.sources.show = self._get_sources_list
        self.sources.browse = self._browse_source

        self.system = SubMenu()
        self.system.heart_beat = self._heart_beat
        self.system.info = self._info

        self.stations = SubMenu()
        self.stations.search = self._search_station

    def _submenus_string(self):
        # ret = dict()
        ret_string = ""
        menus_names = dir(self)
        menus_names = [m for m in menus_names if isinstance(getattr(self, m), SubMenu)]
        for m in menus_names:
            ret_string += f"\n {m}"
            menu = getattr(self, m)
            submenu_names = menu._get_childs()
            # ret[m] = dict()
            for s in submenu_names:
                func = getattr(menu, s)
                pars = inspect.signature(func).parameters
                pars_string = ""
                for key, value in pars.items():
                    pars_string += f"{key} "
                pars_string = pars_string.rstrip()
                if pars_string != "":
                    ret_string += f"\n - {s} [{pars_string}]"
                else:
                    ret_string += f"\n - {s}"
                # ret[m][s] = pars_string
        ret_string = ret_string.lstrip("\n")
        return ret_string

    def _make_message(self, group, command, **kwargs):
        msg = f"heos://{group}/{command}?"
        for key, value in kwargs.items():
            msg += f"{key}={value}&"
        msg = msg.rstrip("&")
        return msg

    def _recv(self, short_answer=False):
        ret = ""
        while not ret.endswith("\r\n"):
            ret += self._sock.recv(2048).decode("utf8")
        if self._verbose:
            print("received", ret)

        ret = parse_json(ret)

        if "STATUS" in ret and ret["STATUS"] == "command under process":
            if self._verbose:
                print("work in progress, triggering re-reading")
            time.sleep(0.5)
            return self._recv(short_answer=short_answer)

        if short_answer:
            if "ANSWER" in ret:
                return ret["ANSWER"]
            else:
                return dict()
        return ret

    def _query_msg(self, msg, short_answer=False):
        if self._verbose:
            print("sending", msg)
        msg += "\n\r"
        msg = msg.encode("utf8")
        self._sock.send(msg)
        time.sleep(TIME_AFTER_SENDING_BEFORE_RECEIVING)
        return self._recv(short_answer=short_answer)

    def _query(self, group, command, short_answer=True, **kwargs):
        msg = self._make_message(group, command, **kwargs)
        return self._query_msg(msg, short_answer=short_answer)

    def _system(self, command, short_answer=True, **kwargs):
        return self._query("system", command, short_answer=short_answer, **kwargs)

    def _player(self, command, short_answer=True, **kwargs):
        if "pid" not in kwargs:
            kwargs["pid"] = self._pid
        return self._query("player", command, short_answer=short_answer, **kwargs)

    def _browse(self, command, short_answer=True, **kwargs):
        return self._query("browse", command, short_answer=short_answer, **kwargs)

    ## SYSTEM SECTION ##
    def _heart_beat(self):
        return self._system("heart_beat")

    ## PLAYER SECTION ##
    def _info(self):
        return self._player("get_player_info")

    def _mute(self):
        return self._player("set_mute", state="on")

    def _unmute(self):
        return self._player("set_mute", state="off")

    def _get_volume(self):
        return int(self._player("get_volume")["level"])

    def _set_volume(self, value):
        return self._player("set_volume", level=value)

    def _volume_up(self, step=2):
        if step > 10:
            step = 10
        if step < 1:
            step = 1
        self._player("volume_up", step=step)

    def _volume_down(self, step=2):
        if step > 10:
            step = 10
        if step < 1:
            step = 1
        self._player("volume_down", step=step)

    def _what_is_playing(self):
        ret = self._player("get_now_playing_media")
        return parse_what_is_playing(ret)

    def _play_previous(self):
        return self._player("play_previous")

    def _play_next(self):
        return self._player("play_next")

    def _play(self, what):
        """ Switch input to `what` """
        return self._browse("play_input", pid=self._pid, input=f"inputs/{what}")

    def _radio(self):
        self._play("tuner")

    def _cd(self):
        self._play("cd")

    def _optical1(self):
        self._play("optical_in_1")

    def _get_sources(self):
        if self._SID is None:
            ret = self._browse("get_music_sources")
            SID = dict()
            for r in ret:
                SID[r["name"]] = r["sid"]
            self._SID = SID
        return self._SID

    def _get_sources_list(self):
        r = self._get_sources()
        return list(r.keys())

    def _browse_source(self, source):
        self._get_sources()
        if source not in self._SID:
            print(f"Can't find '{source}', available sources are {self.get_sources()}")
            return dict()
        return self._browse("browse", sid=self._SID[source])

    def _play_favorite(self, preset):
        return self._browse("play_preset", pid=self._pid, preset=preset)

    def _show_favorites(self):
        ret = self._browse_source("Favorites")
        fav = dict()
        for i, r in enumerate(ret, start=1):
            fav[i] = r["name"]
        return fav

    def _search_station(self, search_string):
        self._get_sources()
        scid = self._browse("get_search_criteria", sid=self._SID["TuneIn"])["scid"]
        return self._browse(
            "search", sid=self._SID["TuneIn"], scid=scid, search=search_string
        )

    def __repr__(self):
        info = self.system.info()
        name = info["name"]

        s = name + f" (volume @ {self.volume.get()})"

        playing = self.play.playing()

        s += f"\n{playing}"
        return s

    def __str__(self):
        return self.__repr__()


if __name__ == "__main__":
    h = HEOS()
    print(str(h))
