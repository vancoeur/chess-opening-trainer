from opening_trainer.mastery import mastery_bucket, summarize_mastery


def test_untrained_is_neu():
    assert mastery_bucket(0, 0.0) == "neu"
    assert mastery_bucket(0, 1.0) == "neu"


def test_high_accuracy_is_sitzt():
    assert mastery_bucket(10, 0.9) == "sitzt"
    assert mastery_bucket(2, 0.85) == "sitzt"   # genau auf der Schwelle


def test_low_accuracy_is_wackelt():
    assert mastery_bucket(10, 0.84) == "wackelt"
    assert mastery_bucket(1, 0.0) == "wackelt"


def test_summarize_counts_each_bucket():
    items = [
        (0, 0.0),     # neu
        (5, 0.9),     # sitzt
        (5, 1.0),     # sitzt
        (3, 0.5),     # wackelt
    ]
    counts = summarize_mastery(items)
    assert counts == {"sitzt": 2, "wackelt": 1, "neu": 1}


def test_summarize_empty():
    assert summarize_mastery([]) == {"sitzt": 0, "wackelt": 0, "neu": 0}
