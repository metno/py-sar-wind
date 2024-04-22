import os
import pytest
import logging
import datetime
import tempfile

from pytz import timezone
from argparse import ArgumentParser

from sarwind.sarwind import SARWind
from sarwind.script.process_sar_wind import main
from sarwind.script.process_sar_wind import process
from sarwind.script.process_sar_wind import create_parser
from sarwind.script.process_sar_wind import process_with_meps
from sarwind.script.process_sar_wind import process_with_arome


logger = logging.getLogger(__name__)


@pytest.mark.sarwind
def testProcess_sar_wind_process(monkeypatch, caplog):
    """Test function process in process_sar_wind.py
    """
    def raise_(ex):
        raise ex

    caplog.set_level(logging.DEBUG)
    with monkeypatch.context() as mp:
        mp.setattr(SARWind, "__init__", lambda *a, **k: raise_(Exception("Hei")))
        process("sar_url", "model_url", "path/to/out", "ending.nc")
        assert "Hei" in caplog.text

        mp.setattr(SARWind, "__init__", lambda *a, **k: raise_(ValueError("Hei")))
        process("sar_url", "model_url", "path/to/out", "ending.nc")
        assert "Hei" in caplog.text

        mp.setattr(SARWind, "__init__", lambda *a, **k: None)
        mp.setattr(SARWind, "export", lambda *a, **k: None)
        mp.setattr(SARWind, "filename", "/some/path/sar_url.nc")
        fn = process("/some/path/sar_url.nc", "model_url.nc", "/path/to/out", "_ending.nc")
        assert fn == "/path/to/out/sar_url_ending.nc"


@pytest.mark.sarwind
def testProcess_sar_wind_process_with_meps(monkeypatch):
    """Test process_with_meps
    """
    fn_out = "/path/to/out/sar_url_ending.nc"
    with monkeypatch.context() as mp:
        mp.setattr("sarwind.script.process_sar_wind.process",
                   lambda *a, **k: fn_out)
        fn = process_with_meps("/some/path/sar_url.nc", "model_url.nc", "/path/to/out")
        assert fn == fn_out

@pytest.mark.sarwind
def testProcess_sar_wind_process_with_arome(monkeypatch):
    """Test process_with_arome
    """
    fn_out = "/path/to/out/sar_url_ending.nc"
    with monkeypatch.context() as mp:
        mp.setattr("sarwind.script.process_sar_wind.process",
                   lambda *a, **k: fn_out)
        fn = process_with_arome("/some/path/sar_url.nc", "model_url.nc", "/path/to/out")
        assert fn == fn_out


@pytest.mark.sarwind
def testProcess_sar_wind_create_parser(monkeypatch, caplog):
    """Test create_parser
    """
    p = create_parser()
    assert isinstance(p, ArgumentParser)


@pytest.mark.sarwind
def testProcess_sar_wind_main(monkeypatch):
    """Test main function of the process_sar_wind script.
    """
    sar_urls = ["/path/to/sar/fn.nc"]
    meps = "https://opendap.url.no/of/a/meps/dataset.nc"
    arome = "https://opendap.url.no/of/a/arome/dataset.nc"
    out_fn_meps = "sar_meps_wind.nc"
    out_fn_arome = "sar_arome_wind.nc"
    class MockArgs:
        pass
    args = MockArgs()
    args.time = datetime.datetime.now(timezone("utc")).isoformat()
    args.delta = 24
    args.output_path = "/path/to/out"
    with monkeypatch.context() as mp:
        mp.setattr("sarwind.script.process_sar_wind.get_sar",
                   lambda *a, **k: sar_urls)
        mp.setattr("sarwind.script.process_sar_wind.collocate_with",
                   lambda *a, **k: (meps, arome))
        mp.setattr("sarwind.script.process_sar_wind.process_with_meps",
                   lambda *a, **k: out_fn_meps)
        mp.setattr("sarwind.script.process_sar_wind.process_with_arome",
                   lambda *a, **k: out_fn_arome)

        # NOTE: the file is opened in binary mode, so the text will be
        #       byte-like in this case.
        with tempfile.NamedTemporaryFile(delete=True) as fp:
            args.processed = fp.name
            main(args)
            assert os.path.isfile(fp.name)
            lines = fp.readlines()
            assert b"/path/to/sar/fn.nc" in lines[0]
            assert b"/path/to/sar/fn.nc" in lines[1]
        assert not os.path.isfile(fp.name)
