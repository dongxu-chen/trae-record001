import os
from typing import Optional, Dict


class ID3Reader:
    SUPPORTED_EXTENSIONS = {'.mp3', '.flac'}

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._tags: Optional[Dict[str, str]] = None

    def _decode_text(self, text) -> str:
        if text is None:
            return ''
        try:
            s = str(text)
            s = s.encode('utf-8', errors='ignore').decode('utf-8')
            return s
        except (UnicodeDecodeError, UnicodeEncodeError):
            return str(text)
        except Exception:
            return ''

    def _load_mp3_tags(self) -> Dict[str, str]:
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, TPE1, TIT2, TALB, TRCK, TDRC, TCON
            audio = MP3(self.file_path, ID3=ID3)
            tags = {}
            if 'TPE1' in audio:
                tags['artist'] = self._decode_text(audio['TPE1'].text[0])
            if 'TIT2' in audio:
                tags['title'] = self._decode_text(audio['TIT2'].text[0])
            if 'TALB' in audio:
                tags['album'] = self._decode_text(audio['TALB'].text[0])
            if 'TRCK' in audio:
                tags['track'] = self._decode_text(audio['TRCK'].text[0]).split('/')[0].zfill(2)
            if 'TDRC' in audio:
                tags['year'] = self._decode_text(audio['TDRC'].text[0])[:4]
            if 'TCON' in audio:
                tags['genre'] = self._decode_text(audio['TCON'].text[0])
            return tags
        except ImportError:
            raise ImportError("mutagen library is required. Install with: pip install mutagen")
        except Exception:
            return {}

    def _load_flac_tags(self) -> Dict[str, str]:
        try:
            from mutagen.flac import FLAC
            audio = FLAC(self.file_path)
            tags = {}
            if 'artist' in audio:
                tags['artist'] = audio['artist'][0]
            if 'title' in audio:
                tags['title'] = audio['title'][0]
            if 'album' in audio:
                tags['album'] = audio['album'][0]
            if 'tracknumber' in audio:
                tags['track'] = audio['tracknumber'][0].split('/')[0].zfill(2)
            if 'date' in audio:
                tags['year'] = audio['date'][0][:4]
            if 'genre' in audio:
                tags['genre'] = audio['genre'][0]
            return tags
        except ImportError:
            raise ImportError("mutagen library is required. Install with: pip install mutagen")
        except Exception:
            return {}

    def read(self) -> Dict[str, str]:
        if self._tags is not None:
            return self._tags

        ext = os.path.splitext(self.file_path)[1].lower()
        if ext == '.mp3':
            self._tags = self._load_mp3_tags()
        elif ext == '.flac':
            self._tags = self._load_flac_tags()
        else:
            self._tags = {}

        return self._tags

    def _write_mp3_tags(self, tags: Dict[str, str]):
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, TPE1, TIT2, TALB, TRCK, TDRC, TCON
            audio = MP3(self.file_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            if 'artist' in tags:
                audio.tags['TPE1'] = TPE1(encoding=3, text=[tags['artist']])
            if 'title' in tags:
                audio.tags['TIT2'] = TIT2(encoding=3, text=[tags['title']])
            if 'album' in tags:
                audio.tags['TALB'] = TALB(encoding=3, text=[tags['album']])
            if 'track' in tags:
                audio.tags['TRCK'] = TRCK(encoding=3, text=[tags['track']])
            if 'year' in tags:
                audio.tags['TDRC'] = TDRC(encoding=3, text=[tags['year']])
            if 'genre' in tags:
                audio.tags['TCON'] = TCON(encoding=3, text=[tags['genre']])
            audio.save()
        except ImportError:
            raise ImportError("mutagen library is required. Install with: pip install mutagen")
        except Exception as e:
            raise e

    def _write_flac_tags(self, tags: Dict[str, str]):
        try:
            from mutagen.flac import FLAC
            audio = FLAC(self.file_path)
            if 'artist' in tags:
                audio['artist'] = [tags['artist']]
            if 'title' in tags:
                audio['title'] = [tags['title']]
            if 'album' in tags:
                audio['album'] = [tags['album']]
            if 'track' in tags:
                audio['tracknumber'] = [tags['track']]
            if 'year' in tags:
                audio['date'] = [tags['year']]
            if 'genre' in tags:
                audio['genre'] = [tags['genre']]
            audio.save()
        except ImportError:
            raise ImportError("mutagen library is required. Install with: pip install mutagen")
        except Exception as e:
            raise e

    def write(self, tags: Dict[str, str]):
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext == '.mp3':
            self._write_mp3_tags(tags)
        elif ext == '.flac':
            self._write_flac_tags(tags)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")
        self._tags = None

    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in cls.SUPPORTED_EXTENSIONS
