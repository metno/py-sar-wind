import pytest

from collocation.with_dataset import SearchCSW
from collocation.with_dataset import AromeArctic
from collocation.with_dataset import Meps

from sarwind.search_and_collocate import get_sar
from sarwind.search_and_collocate import collocate_with


@pytest.mark.sarwind
def test_get_sar(monkeypatch):
    """Test get_sar function.
    """
    urls = [
        "https://nbstds.met.no/thredds/dodsC/NBS/S1A/2024/04/21/IW/"
        "S1A_IW_GRDM_1SDV_20240421T155158_20240421T155225_053534_067F5F_53CE.nc",
        "https://nbstds.met.no/thredds/dodsC/NBS/S1A/2024/04/21/IW/"
        "S1A_IW_GRDM_1SDV_20240421T155109_20240421T155135_053534_067F5F_5AA8.nc",
        "https://nbstds.met.no/thredds/dodsC/NBS/S1A/2024/04/21/IW/"
        "S1A_IW_GRDM_1SDV_20240421T155133_20240421T155200_053534_067F5F_06E5.nc"]
    with monkeypatch.context() as mp:
        mp.setattr(SearchCSW, "__init__", lambda *a, **k: None)
        mp.setattr(SearchCSW, "__getattribute__", lambda *a, **k: urls)
        sar_urls = get_sar()
        assert sar_urls[0] == urls[0]


@pytest.mark.sarwind
def test_collocate_with(monkeypatch):
    """Test function collocate_with.
    """
    url = ("https://nbstds.met.no/thredds/dodsC/NBS/S1A/2024/04/21/"
           "IW/S1A_IW_GRDM_1SDV_20240421T155133_20240421T155200_053534_067F5F_06E5.nc")
    meps = ("https://thredds.met.no/thredds/dodsC/meps25epsarchive/"
            "2024/04/21/15/meps_mbr000_sfc_20240421T15Z.ncml")
    arome = ("https://thredds.met.no/thredds/dodsC/aromearcticarchive/"
             "2024/04/21/arome_arctic_det_2_5km_20240421T15Z.nc")
    with monkeypatch.context() as mp:
        mp.setattr(Meps, "__init__", lambda *a, **k: None)
        mp.setattr(Meps, "get_odap_url_of_nearest", lambda *a, **k: meps)
        mp.setattr(AromeArctic, "__init__", lambda *a, **k: None)
        mp.setattr(AromeArctic, "get_odap_url_of_nearest", lambda *a, **k: arome)
        m, a = collocate_with(url)
        assert m == meps
        assert a == arome
