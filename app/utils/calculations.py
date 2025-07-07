# app/utils/calculations.py

def calculate_trade_pnl(entry_price: float, exit_price: float, quantity: float, direction: str) -> float:
    """
    Calculates the Profit and Loss (PnL) for a trade.

    Args:
        entry_price (float): The price at which the trade was entered.
        exit_price (float): The price at which the trade was exited.
        quantity (float): The size of the trade (e.g., number of shares, contracts).
        direction (str): The direction of the trade, either 'long' or 'short'.

    Returns:
        float: The calculated PnL.
    """
    if direction.lower() == 'long':
        pnl = (exit_price - entry_price) * quantity
    elif direction.lower() == 'short':
        pnl = (entry_price - exit_price) * quantity
    else:
        # Return 0 or raise an error if the direction is invalid
        pnl = 0.0

    return round(pnl, 2)


def calculate_risk_reward_ratio(entry_price: float, stop_loss_price: float, take_profit_price: float) -> float | None:
    """
    Calculates the risk-to-reward ratio for a trade setup.

    Args:
        entry_price (float): The planned entry price.
        stop_loss_price (float): The price at which to exit for a loss.
        take_profit_price (float): The price at which to exit for a profit.

    Returns:
        float | None: The calculated risk/reward ratio, or None if risk is zero.
    """
    # For both long and short positions, risk and reward are absolute distances
    risk = abs(entry_price - stop_loss_price)
    reward = abs(take_profit_price - entry_price)

    if risk == 0:
        # Avoid division by zero
        return None

    ratio = reward / risk
    return round(ratio, 2)