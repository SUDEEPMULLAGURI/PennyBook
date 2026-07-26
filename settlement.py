import json

def calculate_split(total_amount, split_type, members, details):
    """
    Calculates the exact share of each member based on split parameters.
    Returns: dict {member_name: share_amount}
    
    Parameters:
    - total_amount: float
    - split_type: str ('equal', 'unequal', 'percentage', 'quantity', 'item')
    - members: list of str (all member names in the group/split)
    - details: dict with parameters depending on split_type:
      - 'equal': {'participants': [list of member names]} (defaults to all members if empty)
      - 'unequal': {'shares': {member_name: amount}}
      - 'percentage': {'percentages': {member_name: percentage_float}}
      - 'quantity': {'quantities': {member_name: qty_int}}
      - 'item': {'items': [{'name': str, 'price': float, 'consumers': [list of str]}], 
                 'tax': float, 'tip': float, 'tax_tip_split': str ('proportional' or 'equal')}
    """
    total_amount = float(total_amount)
    shares = {m: 0.0 for m in members}
    
    if split_type == 'equal':
        participants = details.get('participants', [])
        if not participants:
            participants = list(members)
        if not participants:
            return shares
            
        share = total_amount / len(participants)
        for p in participants:
            if p in shares:
                shares[p] = round(share, 2)
                
        # Handle rounding adjustments by applying remainder to the first participant
        sum_shares = sum(shares.values())
        remainder = round(total_amount - sum_shares, 2)
        if remainder != 0 and participants[0] in shares:
            shares[participants[0]] = round(shares[participants[0]] + remainder, 2)
            
    elif split_type == 'unequal':
        detail_shares = details.get('shares', {})
        for m in members:
            shares[m] = float(detail_shares.get(m, 0.0))
            
    elif split_type == 'percentage':
        percentages = details.get('percentages', {})
        for m in members:
            pct = float(percentages.get(m, 0.0))
            shares[m] = round(total_amount * (pct / 100.0), 2)
            
        # Adjust rounding
        sum_shares = sum(shares.values())
        remainder = round(total_amount - sum_shares, 2)
        if remainder != 0:
            # Find member with highest percentage and give them the remainder
            active_members = [m for m in members if float(percentages.get(m, 0.0)) > 0]
            if active_members:
                target = max(active_members, key=lambda m: float(percentages.get(m, 0.0)))
                shares[target] = round(shares[target] + remainder, 2)
                
    elif split_type == 'quantity':
        quantities = details.get('quantities', {})
        total_qty = sum(float(q) for q in quantities.values())
        if total_qty <= 0:
            return shares
            
        for m in members:
            qty = float(quantities.get(m, 0.0))
            shares[m] = round(total_amount * (qty / total_qty), 2)
            
        # Adjust rounding
        sum_shares = sum(shares.values())
        remainder = round(total_amount - sum_shares, 2)
        if remainder != 0:
            active_members = [m for m in members if float(quantities.get(m, 0.0)) > 0]
            if active_members:
                target = max(active_members, key=lambda m: float(quantities.get(m, 0.0)))
                shares[target] = round(shares[target] + remainder, 2)
                
    elif split_type == 'item':
        items = details.get('items', [])
        tax = float(details.get('tax', 0.0))
        tip = float(details.get('tip', 0.0))
        tax_tip_split = details.get('tax_tip_split', 'proportional')
        
        # Calculate subtotal of items
        item_subtotal = 0.0
        member_subtotals = {m: 0.0 for m in members}
        
        for item in items:
            price = float(item.get('price', 0.0))
            item_subtotal += price
            consumers = item.get('consumers', [])
            if not consumers:
                consumers = list(members) # Default to all if empty
                
            share = price / len(consumers)
            for c in consumers:
                if c in member_subtotals:
                    member_subtotals[c] += share
                    
        # If total_amount wasn't passed directly, let's treat subtotal + tax + tip as total
        if total_amount <= 0:
            total_amount = item_subtotal + tax + tip
            
        if item_subtotal <= 0:
            # If no items, split everything equally
            return calculate_split(total_amount, 'equal', members, {})
            
        # Distribute tax and tip
        for m in members:
            sub = member_subtotals[m]
            if sub <= 0:
                continue
                
            # Proportional calculation
            if tax_tip_split == 'proportional':
                m_tax = tax * (sub / item_subtotal)
                m_tip = tip * (sub / item_subtotal)
                shares[m] = round(sub + m_tax + m_tip, 2)
            else: # Equal split of tax/tip
                # Find number of active consumers in the entire bill
                active_consumers = sum(1 for sub_t in member_subtotals.values() if sub_t > 0)
                m_tax = tax / active_consumers
                m_tip = tip / active_consumers
                shares[m] = round(sub + m_tax + m_tip, 2)
                
        # Adjust rounding to match total_amount
        sum_shares = sum(shares.values())
        remainder = round(total_amount - sum_shares, 2)
        if remainder != 0:
            active_members = [m for m in members if member_subtotals[m] > 0]
            if active_members:
                target = max(active_members, key=lambda m: member_subtotals[m])
                shares[target] = round(shares[target] + remainder, 2)
                
    return shares

def calculate_settlements(balances):
    """
    Computes the minimum number of payments to settle running balances.
    balances: dict of {member_name: net_balance}
              where net_balance = total_paid - total_owed
              Positive balance means the group owes them (Creditor)
              Negative balance means they owe the group (Debtor)
              
    Returns: list of dicts [{"from": debtor, "to": creditor, "amount": float}]
    """
    # Clean floating point precision issues (balances should sum to 0)
    for m in balances:
        balances[m] = round(balances[m], 2)
        
    # Filter and split into Debtors and Creditors
    debtors = []   # (name, debt_amount_positive)
    creditors = []  # (name, credit_amount)
    
    for name, bal in balances.items():
        if bal < -0.01:
            debtors.append((name, abs(bal)))
        elif bal > 0.01:
            creditors.append((name, bal))
            
    # Sort descending by value to settle largest amounts first
    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)
    
    payments = []
    
    i = 0  # debtor index
    j = 0  # creditor index
    
    # We copy list elements into mutable lists
    debtors = [[d[0], d[1]] for d in debtors]
    creditors = [[c[0], c[1]] for c in creditors]
    
    while i < len(debtors) and j < len(creditors):
        debtor_name, debt_amt = debtors[i]
        creditor_name, credit_amt = creditors[j]
        
        if debt_amt <= 0.01:
            i += 1
            continue
        if credit_amt <= 0.01:
            j += 1
            continue
            
        settle_amt = min(debt_amt, credit_amt)
        payments.append({
            "from": debtor_name,
            "to": creditor_name,
            "amount": round(settle_amt, 2)
        })
        
        # Update balances
        debtors[i][1] -= settle_amt
        creditors[j][1] -= settle_amt
        
        if debtors[i][1] <= 0.01:
            i += 1
        if creditors[j][1] <= 0.01:
            j += 1
            
    return payments
