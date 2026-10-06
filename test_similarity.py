"""Run:  python test_similarity.py     (from the MysteryMatrix folder)"""
import math
import similarity as s

def close(a, b, tol=1e-6):
    return abs(a - b) < tol

def test_basic_math():
    assert s.dot_product([1, 2, 3], [4, 5, 6]) == 32
    assert close(s.vector_magnitude([3, 4]), 5)
    assert close(s.vector_magnitude(s.normalize_vector([3, 4])), 1)
    assert s.normalize_vector([0, 0]) == [0.0, 0.0]
    assert close(s.cosine_similarity([1, 0], [0, 1]), 0)
    assert close(s.cosine_similarity([2, 2], [1, 1]), 1)
    assert close(s.cosine_similarity([1, 0], [-1, 0]), -1)
    assert s.cosine_similarity([0, 0], [1, 2]) is None
    try:
        s.dot_product([1], [1, 2]); assert False
    except ValueError:
        pass

def test_reference_values():
    m = s.build_case_matrix("evidence.csv")
    assert m["C01"] == [4, 1, 3, 5, 5, 4, 4, 1, 0]
    r = s.compare_cases(m, "C01", "C02")
    assert r["dot"] == 79
    assert close(r["mag_a"], 10.4403, 1e-4) and close(r["mag_b"], 11.4018, 1e-4)
    assert close(r["cosine"], 0.6636547, 1e-6)

def test_matrix_properties():
    ids, sim = s.calculate_similarity_matrix(s.build_case_matrix("evidence.csv"))
    n = len(ids)
    for i in range(n):
        assert close(sim[i][i], 1)
        for j in range(n):
            assert close(sim[i][j], sim[j][i])
            assert -1 <= sim[i][j] <= 1

def test_binary_matches_member2():
    """Member 2's similarity_results.csv uses presence/absence profiles."""
    ids, sim = s.calculate_similarity_matrix(s.get_matrix("binary"))
    assert close(sim[ids.index("C01")][ids.index("C02")], 0.7071, 1e-4)
    assert close(sim[ids.index("C02")][ids.index("C05")], 0.2041, 1e-4)

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)
    print("All tests passed.")