from matcha.fsm import Card

def test_eq():
    c1 = Card(Card.Suit.CLUBS, Card.Rank.ACE)
    c2 = Card(Card.Suit.CLUBS, Card.Rank.ACE)
    assert(c1 == c2)

def test_eq_same_suit_diff_rank():
    c1 = Card(Card.Suit.CLUBS, Card.Rank.ACE)
    c2 = Card(Card.Suit.CLUBS, Card.Rank.SEVEN)
    assert((c1 == c2) == False)

def test_eq_diff_suit():
    c1 = Card(Card.Suit.CLUBS, Card.Rank.ACE)
    c2 = Card(Card.Suit.HEARTS, Card.Rank.ACE)
    assert((c1 == c2) == False)

def test_le():
    c1 = Card(Card.Suit.HEARTS, Card.Rank.ACE)
    c2 = Card(Card.Suit.CLUBS, Card.Rank.ACE)
    assert(c1 < c2)

def test_gt():
    c1 = Card(Card.Suit.CLUBS, Card.Rank.ACE)
    c2 = Card(Card.Suit.HEARTS, Card.Rank.ACE)
    assert((c1 < c2) == False)

def test_le_same_suit():
    c1 = Card(Card.Suit.CLUBS, Card.Rank.TEN)
    c2 = Card(Card.Suit.CLUBS, Card.Rank.ACE)
    assert(c1 < c2)

def test_le_same_suit_seven():
    c1 = Card(Card.Suit.CLUBS, Card.Rank.SEVEN)
    c2 = Card(Card.Suit.CLUBS, Card.Rank.KING)
    assert(c1 < c2)

def test_le_same_suit_seven_not():
    c1 = Card(Card.Suit.CLUBS, Card.Rank.KING)
    c2 = Card(Card.Suit.CLUBS, Card.Rank.SEVEN)
    assert(not (c1 < c2))
