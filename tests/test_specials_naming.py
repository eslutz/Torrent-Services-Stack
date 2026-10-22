"""Season-zero episodes must not be rendered into Jellyfin's bonus folder."""
import json
from pathlib import Path
import unittest

class SpecialsNamingTest(unittest.TestCase):
 def test_sonarr_specials_are_a_season(self):
  text=(Path(__file__).resolve().parents[1]/'templates/usr/local/libexec/home-network/wire-torrent-apps').read_text()
  naming=json.loads(text.split("<<'SONARR_NAMING'\n",1)[1].split('\nSONARR_NAMING',1)[0])
  self.assertEqual(naming['specialsFolderFormat'],'Season 00')
  self.assertTrue(naming['renameEpisodes'])
  self.assertIn('S{season:00}E{episode:00}',naming['standardEpisodeFormat'])
if __name__=='__main__':unittest.main()
