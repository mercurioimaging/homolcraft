from homolcraft.core.pairs import all_pairs

def test_all_pairs():
    images = ["a.jpg", "b.jpg", "c.jpg"]
    pairs = all_pairs(images)
    assert ("a.jpg", "b.jpg") in pairs
    assert ("a.jpg", "c.jpg") in pairs
    assert ("b.jpg", "c.jpg") in pairs
    assert len(pairs) == 3 