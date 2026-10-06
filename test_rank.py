from rank_analysis import (
    calculate_rank_from_rref,
    find_pivot_columns,
    get_pivot_features
)


# Test 1: Full-rank 2x2 matrix
def test_full_rank():
    rref = [
        [1, 0],
        [0, 1]
    ]

    assert calculate_rank_from_rref(rref) == 2
    assert find_pivot_columns(rref) == [0, 1]


# Test 2: Rank-deficient matrix
def test_rank_deficient():
    rref = [
        [1, 2],
        [0, 0]
    ]

    assert calculate_rank_from_rref(rref) == 1
    assert find_pivot_columns(rref) == [0]


# Test 3: Zero matrix
def test_zero_matrix():
    rref = [
        [0, 0, 0],
        [0, 0, 0]
    ]

    assert calculate_rank_from_rref(rref) == 0
    assert find_pivot_columns(rref) == []


# Test 4: Rectangular matrix
def test_rectangular_matrix():
    rref = [
        [1, 0, 3],
        [0, 1, 4],
        [0, 0, 0]
    ]

    assert calculate_rank_from_rref(rref) == 2
    assert find_pivot_columns(rref) == [0, 1]


# Test 5: Pivot features
def test_pivot_features():
    pivot_columns = [0, 1, 3]

    expected_features = [
        "physical",
        "biological",
        "documentary"
    ]

    assert get_pivot_features(pivot_columns) == expected_features


print("All 5 tests passed!")