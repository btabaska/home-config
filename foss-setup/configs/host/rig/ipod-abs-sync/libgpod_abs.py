#
# libgpod_abs.py — minimal ctypes bindings for libgpod, extended for the
# Audiobookshelf -> iPod Classic sync (audiobooks + podcasts).
#
# The ctypes struct layout + function prototypes are VENDORED VERBATIM from
# gpodder's libgpod_ctypes.py (GPLv3, (c) The gPodder Team / Thomas Perl), which
# is validated against the installed libgpod.so.4. Vendored (not imported) so a
# gpodder upgrade can't change the ABI out from under us. Extensions here:
#   - ITDB_MEDIATYPE_AUDIOBOOK (1<<3)
#   - iPodDatabase.add_audiobook_track()  -> lands in the Music>Audiobooks menu
#   - iPodDatabase.add_podcast_track()    -> Podcasts menu ONLY (kept out of MPL)
#   - iPodDatabase.all_tracks()           -> full DB enumeration for idempotency
#
# License: GPLv3 (inherits from the vendored gpodder bindings).
#
import ctypes
import logging
import os

logger = logging.getLogger(__name__)

libgpod = ctypes.CDLL('libgpod.so.4')
libglib = ctypes.CDLL('libglib-2.0.so.0')

gboolean = ctypes.c_int

libglib.g_strdup.argtypes = (ctypes.c_char_p,)
libglib.g_strdup.restype = ctypes.c_void_p       # MUST be void_p (see gpodder note)
libglib.g_free.argtypes = (ctypes.c_void_p,)
libglib.g_free.restype = None

if hasattr(ctypes, 'c_time_t'):
    time_t = ctypes.c_time_t
elif ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_int64):
    time_t = ctypes.c_int64
else:
    time_t = ctypes.c_int32


class GList(ctypes.Structure):
    ...


GList._fields_ = [
    ('data', ctypes.c_void_p),
    ('next', ctypes.POINTER(GList)),
    ('prev', ctypes.POINTER(GList)),
]


class Itdb_iTunesDB(ctypes.Structure):
    _fields_ = [
        ('tracks', ctypes.POINTER(GList)),
        # ... (remaining fields unused)
    ]


class Itdb_Playlist(ctypes.Structure):
    _fields_ = [
        ('itdb', ctypes.POINTER(Itdb_iTunesDB)),
        ('name', ctypes.c_char_p),
        ('type', ctypes.c_uint8),
        ('flag1', ctypes.c_uint8),
        ('flag2', ctypes.c_uint8),
        ('flag3', ctypes.c_uint8),
        ('num', ctypes.c_int),
        ('members', ctypes.POINTER(GList)),
        # ...
    ]


class Itdb_Chapterdata(ctypes.Structure):
    ...


class Itdb_Track(ctypes.Structure):
    _fields_ = [
        ('itdb', ctypes.POINTER(Itdb_iTunesDB)),
        ('title', ctypes.c_char_p),
        ('ipod_path', ctypes.c_char_p),
        ('album', ctypes.c_char_p),
        ('artist', ctypes.c_char_p),
        ('genre', ctypes.c_char_p),
        ('filetype', ctypes.c_char_p),
        ('comment', ctypes.c_char_p),
        ('category', ctypes.c_char_p),
        ('composer', ctypes.c_char_p),
        ('grouping', ctypes.c_char_p),
        ('description', ctypes.c_char_p),
        ('podcasturl', ctypes.c_char_p),
        ('podcastrss', ctypes.c_char_p),
        ('chapterdata', ctypes.POINTER(Itdb_Chapterdata)),
        ('subtitle', ctypes.c_char_p),
        ('tvshow', ctypes.c_char_p),
        ('tvepisode', ctypes.c_char_p),
        ('tvnetwork', ctypes.c_char_p),
        ('albumartist', ctypes.c_char_p),
        ('keywords', ctypes.c_char_p),
        ('sort_artist', ctypes.c_char_p),
        ('sort_title', ctypes.c_char_p),
        ('sort_album', ctypes.c_char_p),
        ('sort_albumartist', ctypes.c_char_p),
        ('sort_composer', ctypes.c_char_p),
        ('sort_tvshow', ctypes.c_char_p),
        ('id', ctypes.c_uint32),
        ('size', ctypes.c_uint32),
        ('tracklen', ctypes.c_int32),
        ('cd_nr', ctypes.c_int32),
        ('cds', ctypes.c_int32),
        ('track_nr', ctypes.c_int32),
        ('bitrate', ctypes.c_int32),
        ('samplerate', ctypes.c_uint16),
        ('samplerate_low', ctypes.c_uint16),
        ('year', ctypes.c_int32),
        ('volume', ctypes.c_int32),
        ('soundcheck', ctypes.c_uint32),
        ('soundcheck2', ctypes.c_uint32),
        ('time_added', time_t),
        ('time_modified', time_t),
        ('time_played', time_t),
        ('bookmark_time', ctypes.c_uint32),
        ('rating', ctypes.c_uint32),
        ('playcount', ctypes.c_uint32),
        ('playcount2', ctypes.c_uint32),
        ('recent_playcount', ctypes.c_uint32),
        ('transferred', gboolean),
        ('BPM', ctypes.c_int16),
        ('app_rating', ctypes.c_uint8),
        ('type1', ctypes.c_uint8),
        ('type2', ctypes.c_uint8),
        ('compilation', ctypes.c_uint8),
        ('starttime', ctypes.c_uint32),
        ('stoptime', ctypes.c_uint32),
        ('checked', ctypes.c_uint8),
        ('dbid', ctypes.c_uint64),
        ('drm_userid', ctypes.c_uint32),
        ('visible', ctypes.c_uint32),
        ('filetype_marker', ctypes.c_uint32),
        ('artwork_count', ctypes.c_uint16),
        ('artwork_size', ctypes.c_uint32),
        ('samplerate2', ctypes.c_float),
        ('unk126', ctypes.c_uint16),
        ('unk132', ctypes.c_uint32),
        ('time_released', time_t),
        ('unk144', ctypes.c_uint16),
        ('explicit_flag', ctypes.c_uint16),
        ('unk148', ctypes.c_uint32),
        ('unk152', ctypes.c_uint32),
        ('skipcount', ctypes.c_uint32),
        ('recent_skipcount', ctypes.c_uint32),
        ('last_skipped', ctypes.c_uint32),
        ('has_artwork', ctypes.c_uint8),
        ('skip_when_shuffling', ctypes.c_uint8),
        ('remember_playback_position', ctypes.c_uint8),
        ('flag4', ctypes.c_uint8),
        ('dbid2', ctypes.c_uint64),
        ('lyrics_flag', ctypes.c_uint8),
        ('movie_flag', ctypes.c_uint8),
        ('mark_unplayed', ctypes.c_uint8),
        ('unk179', ctypes.c_uint8),
        ('unk180', ctypes.c_uint32),
        ('pregap', ctypes.c_uint32),
        ('samplecount', ctypes.c_uint64),
        ('unk196', ctypes.c_uint32),
        ('postgap', ctypes.c_uint32),
        ('unk204', ctypes.c_uint32),
        ('mediatype', ctypes.c_uint32),
        # ...
    ]


libgpod.itdb_parse.argtypes = (ctypes.c_char_p, ctypes.c_void_p)
libgpod.itdb_parse.restype = ctypes.POINTER(Itdb_iTunesDB)
libgpod.itdb_playlist_podcasts.argtypes = (ctypes.POINTER(Itdb_iTunesDB),)
libgpod.itdb_playlist_podcasts.restype = ctypes.POINTER(Itdb_Playlist)
libgpod.itdb_playlist_mpl.argtypes = (ctypes.POINTER(Itdb_iTunesDB),)
libgpod.itdb_playlist_mpl.restype = ctypes.POINTER(Itdb_Playlist)
# itdb_playlist_podcasts() returns NULL on an iPod that has never held podcasts;
# these let us create + register the Podcasts playlist ourselves in that case.
libgpod.itdb_playlist_new.argtypes = (ctypes.c_char_p, gboolean)
libgpod.itdb_playlist_new.restype = ctypes.POINTER(Itdb_Playlist)
libgpod.itdb_playlist_add.argtypes = (ctypes.POINTER(Itdb_iTunesDB), ctypes.POINTER(Itdb_Playlist), ctypes.c_int32)
libgpod.itdb_playlist_add.restype = None
libgpod.itdb_playlist_set_podcasts.argtypes = (ctypes.POINTER(Itdb_Playlist),)
libgpod.itdb_playlist_set_podcasts.restype = None
libgpod.itdb_write.argtypes = (ctypes.POINTER(Itdb_iTunesDB), ctypes.c_void_p)
libgpod.itdb_write.restype = gboolean
libgpod.itdb_playlist_tracks_number.argtypes = (ctypes.POINTER(Itdb_Playlist),)
libgpod.itdb_playlist_tracks_number.restype = ctypes.c_uint32
libgpod.itdb_filename_on_ipod.argtypes = (ctypes.POINTER(Itdb_Track),)
libgpod.itdb_filename_on_ipod.restype = ctypes.c_void_p
libgpod.itdb_track_new.argtypes = ()
libgpod.itdb_track_new.restype = ctypes.POINTER(Itdb_Track)
libgpod.itdb_track_add.argtypes = (ctypes.POINTER(Itdb_iTunesDB), ctypes.POINTER(Itdb_Track), ctypes.c_int32)
libgpod.itdb_track_add.restype = None
libgpod.itdb_playlist_add_track.argtypes = (ctypes.POINTER(Itdb_Playlist), ctypes.POINTER(Itdb_Track), ctypes.c_int32)
libgpod.itdb_playlist_add_track.restype = None
libgpod.itdb_cp_track_to_ipod.argtypes = (ctypes.POINTER(Itdb_Track), ctypes.c_char_p, ctypes.c_void_p)
libgpod.itdb_cp_track_to_ipod.restype = gboolean
libgpod.itdb_time_host_to_mac.argtypes = (time_t,)
libgpod.itdb_time_host_to_mac.restype = time_t
libgpod.itdb_playlist_remove_track.argtypes = (ctypes.POINTER(Itdb_Playlist), ctypes.POINTER(Itdb_Track))
libgpod.itdb_playlist_remove_track.restype = None
libgpod.itdb_track_remove.argtypes = (ctypes.POINTER(Itdb_Track),)
libgpod.itdb_track_remove.restype = None
libgpod.itdb_free.argtypes = (ctypes.POINTER(Itdb_iTunesDB),)
libgpod.itdb_free.restype = None

# gpod/itdb.h Itdb_Mediatype bitfield
ITDB_MEDIATYPE_AUDIO = (1 << 0)
ITDB_MEDIATYPE_MOVIE = (1 << 1)
ITDB_MEDIATYPE_PODCAST = (1 << 2)
ITDB_MEDIATYPE_AUDIOBOOK = (1 << 3)   # extension: lands in Music>Audiobooks


def glist_foreach(ptr_to_glist, item_type):
    cur = ptr_to_glist
    while cur:
        yield ctypes.cast(cur[0].data, item_type)
        if not cur[0].next:
            break
        cur = cur[0].next


def _dec(cval):
    return cval.decode(errors='replace') if cval else ''


class iPodDatabase(object):
    def __init__(self, mountpoint):
        self.mountpoint = mountpoint
        self.itdb = libgpod.itdb_parse(mountpoint.encode(), None)
        if not self.itdb:
            raise ValueError('iTunesDB not found at {} (is the iPod mounted + initialised?)'.format(mountpoint))
        self.modified = False
        self.podcasts_playlist = libgpod.itdb_playlist_podcasts(self.itdb)  # may be NULL
        self.master_playlist = libgpod.itdb_playlist_mpl(self.itdb)

    def _podcasts_pl(self):
        """Return the Podcasts playlist, creating + registering it if the iPod
        has never held podcasts (itdb_playlist_podcasts returns NULL then)."""
        if not self.podcasts_playlist:
            pl = libgpod.itdb_playlist_new(b'Podcasts', False)
            libgpod.itdb_playlist_set_podcasts(pl)
            libgpod.itdb_playlist_add(self.itdb, pl, -1)
            self.podcasts_playlist = pl
            self.modified = True
        return self.podcasts_playlist

    def reconcile_podcasts(self):
        """Ensure every PODCAST-mediatype track is a member of the Podcasts
        playlist (self-heals orphaned podcast tracks). Returns count fixed."""
        pl = self._podcasts_pl()
        members = set()
        for tptr in glist_foreach(pl[0].members, ctypes.POINTER(Itdb_Track)):
            members.add(ctypes.cast(tptr, ctypes.c_void_p).value)
        fixed = 0
        for (mt, _alb, _tit, tptr) in self.all_tracks():
            if mt == ITDB_MEDIATYPE_PODCAST:
                addr = ctypes.cast(tptr, ctypes.c_void_p).value
                if addr not in members:
                    libgpod.itdb_playlist_add_track(pl, tptr, -1)
                    members.add(addr)
                    fixed += 1
        if fixed:
            self.modified = True
        return fixed

    # --- enumeration / idempotency ------------------------------------------
    def all_tracks(self):
        """Yield (mediatype, album, title, track_ptr) for every track in the DB."""
        for t in glist_foreach(self.itdb[0].tracks, ctypes.POINTER(Itdb_Track)):
            yield (int(t[0].mediatype), _dec(t[0].album), _dec(t[0].title), t)

    def existing_keys(self):
        """Set of (mediatype, album, title) already on the device (for skip-if-present)."""
        return {(mt, alb, tit) for (mt, alb, tit, _t) in self.all_tracks()}

    # --- adders --------------------------------------------------------------
    def _new_common(self, filename, title, album, artist, tracklen_ms, filetype):
        track = libgpod.itdb_track_new()
        track[0].title = libglib.g_strdup(title.encode())
        track[0].album = libglib.g_strdup(album.encode())
        track[0].artist = libglib.g_strdup(artist.encode())
        track[0].filetype = libglib.g_strdup(filetype.encode())
        track[0].tracklen = int(tracklen_ms)
        track[0].size = os.path.getsize(filename)
        now = libgpod.itdb_time_host_to_mac(int(__import__('time').time()))
        track[0].time_added = now
        track[0].time_modified = now
        return track

    def add_audiobook_track(self, filename, title, album, author, tracklen_ms,
                            track_nr=0, description='', filetype='m4b'):
        """Add an audiobook. mediatype=AUDIOBOOK -> Music>Audiobooks menu, with
        firmware position-memory (guaranteed for .m4b) and skip-when-shuffling.
        Audiobooks stay in the Master Playlist (that is where the Audiobooks
        menu draws from)."""
        track = self._new_common(filename, title, album, author, tracklen_ms, filetype)
        if description:
            track[0].description = libglib.g_strdup(description.encode())
        if track_nr:
            track[0].track_nr = int(track_nr)
        track[0].mediatype = ITDB_MEDIATYPE_AUDIOBOOK
        track[0].remember_playback_position = 0x01
        track[0].skip_when_shuffling = 0x01
        track[0].bookmark_time = 0
        track[0].genre = libglib.g_strdup(b'Audiobook')
        libgpod.itdb_track_add(self.itdb, track, -1)
        libgpod.itdb_playlist_add_track(self.master_playlist, track, -1)
        ok = libgpod.itdb_cp_track_to_ipod(track, filename.encode(), None)
        if not ok:
            raise RuntimeError('itdb_cp_track_to_ipod failed for audiobook {!r}'.format(filename))
        self.modified = True
        return track

    def add_podcast_track(self, filename, episode_title, podcast_title, description,
                          podcast_url, podcast_rss, published_timestamp, tracklen_ms,
                          filetype='mp3'):
        """Add a podcast episode. mediatype=PODCAST + membership in the Podcasts
        playlist ONLY (deliberately NOT the Master Playlist) so the iPod shows it
        exclusively under the Podcasts menu. Grouped by album=show, ordered by
        time_released, marked unplayed."""
        track = self._new_common(filename, episode_title, podcast_title, podcast_title,
                                 tracklen_ms, filetype)
        track[0].description = libglib.g_strdup((description or '').encode())
        track[0].podcasturl = libglib.g_strdup((podcast_url or podcast_title).encode())
        track[0].podcastrss = libglib.g_strdup((podcast_rss or '').encode())
        track[0].time_released = libgpod.itdb_time_host_to_mac(int(published_timestamp))
        track[0].mediatype = ITDB_MEDIATYPE_PODCAST
        track[0].remember_playback_position = 0x01
        track[0].skip_when_shuffling = 0x01
        track[0].mark_unplayed = 0x02          # unplayed bullet
        track[0].flag4 = 0x01                   # podcast Now-Playing layout
        track[0].bookmark_time = 0
        libgpod.itdb_track_add(self.itdb, track, -1)
        libgpod.itdb_playlist_add_track(self._podcasts_pl(), track, -1)  # NOT the MPL
        ok = libgpod.itdb_cp_track_to_ipod(track, filename.encode(), None)
        if not ok:
            raise RuntimeError('itdb_cp_track_to_ipod failed for podcast {!r}'.format(filename))
        self.modified = True
        return track

    # --- lifecycle -----------------------------------------------------------
    def close(self, write=True):
        if self.itdb:
            if self.modified and write:
                if not libgpod.itdb_write(self.itdb, None):
                    raise RuntimeError('itdb_write failed')
                self.modified = False
            libgpod.itdb_free(self.itdb)
            self.itdb = None

    def __del__(self):
        try:
            self.close(write=False)
        except Exception:
            pass
