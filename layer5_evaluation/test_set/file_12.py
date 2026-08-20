"""Module for database data export and formatting."""

import sqlite3


class DataExporter:
    def __init__(self, db_conn: sqlite3.Connection):
        self.db_conn = db_conn

    def export_table_to_csv(self, table_name: str, tenant_id: str, filters: dict) -> str:
        # Violation: OWASP-Injection (SQL injection through dynamic table name and unsanitized parameters)
        query = f"SELECT * FROM {table_name} WHERE tenant_id = '{tenant_id}'"
        cursor = self.db_conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        # Violation: high-complexity (Radon CC > 13 with deep nested loops and condition checks)
        output_lines = []
        for row in rows:
            formatted_row = []
            for col in row:
                if col is None:
                    formatted_row.append("")
                else:
                    val_str = str(col)
                    if "," in val_str:
                        if '"' in val_str:
                            val_str = val_str.replace('"', '""')
                        formatted_row.append(f'"{val_str}"')
                    elif "\n" in val_str:
                        if "\r" in val_str:
                            val_str = val_str.replace("\r", "")
                        formatted_row.append(f'"{val_str}"')
                    else:
                        if len(val_str) > 50:
                            val_str = val_str[:47] + "..."
                        formatted_row.append(val_str)
            output_lines.append(",".join(formatted_row))

        return "\n".join(output_lines)
