"""Module for financial report generation."""

import os
import json


class FinancialReportService:
    # Violation: long-function (> 55 lines) & SRP (fetches raw data, computes taxes, builds HTML, writes to disk, logs metrics)
    def generate_monthly_financial_report(self, raw_transactions: list[dict], month: str, output_dir: str) -> str:
        total_revenue = 0.0
        total_expenses = 0.0
        taxable_income = 0.0
        category_breakdown = {}

        # 1. Processing and summing transactions
        for tx in raw_transactions:
            amount = tx.get("amount", 0.0)
            category = tx.get("category", "General")
            tx_type = tx.get("type", "DEBIT")

            if tx_type == "CREDIT":
                total_revenue += amount
                if category != "TaxExempt":
                    taxable_income += amount
            else:
                total_expenses += amount

            if category not in category_breakdown:
                category_breakdown[category] = 0.0
            category_breakdown[category] += amount

        # 2. Calculating taxes and net margin
        corporate_tax_rate = 0.21
        estimated_tax = taxable_income * corporate_tax_rate
        net_profit = total_revenue - total_expenses - estimated_tax
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

        # 3. Generating HTML presentation markup
        html_lines = []
        html_lines.append("<!DOCTYPE html><html><head><title>Report</title></head><body>")
        html_lines.append(f"<h1>Financial Report for {month}</h1>")
        html_lines.append("<ul>")
        html_lines.append(f"<li>Total Revenue: ${total_revenue:.2f}</li>")
        html_lines.append(f"<li>Total Expenses: ${total_expenses:.2f}</li>")
        html_lines.append(f"<li>Estimated Tax: ${estimated_tax:.2f}</li>")
        html_lines.append(f"<li>Net Profit: ${net_profit:.2f}</li>")
        html_lines.append(f"<li>Profit Margin: {profit_margin:.2f}%</li>")
        html_lines.append("</ul>")
        html_lines.append("<h2>Category Breakdown</h2><table>")
        for cat, total in category_breakdown.items():
            html_lines.append(f"<tr><td>{cat}</td><td>${total:.2f}</td></tr>")
        html_lines.append("</table></body></html>")
        html_content = "\n".join(html_lines)

        # 4. Direct filesystem I/O operations
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"report_{month}.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 5. Writing audit log summary
        log_path = os.path.join(output_dir, "audit_log.json")
        summary = {"month": month, "revenue": total_revenue, "profit": net_profit}
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(summary, f)

        return file_path
