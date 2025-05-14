from homolcraft.core.io import write_micmac_txt

def test_write_micmac_txt(tmp_path):
    points = [
        (1.0, 2.0, 3.0, 4.0, 1.0),
        (5.0, 6.0, 7.0, 8.0, 0.9)
    ]
    out = tmp_path / "out.txt"
    write_micmac_txt(str(out), points)
    lines = out.read_text().splitlines()
    assert lines[0].startswith("1.000000 2.000000 3.000000 4.000000 1.000000")
    assert lines[1].startswith("5.000000 6.000000 7.000000 8.000000 0.900000") 