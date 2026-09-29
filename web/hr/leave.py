"""Leave approval (web version)."""

from hr.database import get_connection


# Leave types that come off a balance kept on the employee record.
LEAVE_BALANCE_COLUMNS = {"Annual": "annual_leave", "Sick": "sick_leave"}


def decide_leave(request_id, status):
    """Approve or reject a pending leave request.

    Approving Annual or Sick leave deducts the days from the employee's
    balance. Returns ``(ok, message)``.
    """
    conn = get_connection()
    try:
        request = conn.execute(
            "SELECT * FROM leave_requests WHERE id = ?", (request_id,)
        ).fetchone()

        if not request:
            return False, "Leave request not found."
        if request["status"] != "Pending":
            return False, "This request has already been processed."

        column = LEAVE_BALANCE_COLUMNS.get(request["leave_type"])
        if status == "Approved" and column:
            balance = conn.execute(
                f"SELECT {column} FROM employees WHERE employee_id = ?",
                (request["employee_id"],)
            ).fetchone()[column]

            if balance < request["days"]:
                return False, (f"Not enough {request['leave_type'].lower()} "
                               f"leave ({balance} day(s) left).")

            conn.execute(
                f"UPDATE employees SET {column} = {column} - ? WHERE employee_id = ?",
                (request["days"], request["employee_id"])
            )

        conn.execute(
            "UPDATE leave_requests SET status = ? WHERE id = ?",
            (status, request_id)
        )
        conn.commit()
        return True, f"Leave request {status.lower()}."
    finally:
        conn.close()
