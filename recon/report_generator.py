import os
import json
import pandas as pd
import plotly.express as px
from datetime import datetime
import webbrowser
from config.env_config import Config


class EvaluationReport:
    def __init__(self, result_dir=None):
        self.result_dir = result_dir or Config.OUTPUT_DIR
        self.detailed_csv = os.path.join(self.result_dir, "detailed_eval_logs.csv")
        self.summary_json = os.path.join(self.result_dir, "summary_eval_logs.json")
        self.buffer_csv = os.path.join(self.result_dir, "buffer_analysis.csv")
        self.buffer_summary_json = os.path.join(self.result_dir, "buffer_summary.json")
        self.model_knowledge_json = os.path.join(
            self.result_dir, "model_knowledge.json"
        )
        self.df_steps = None
        self.summary_data = None
        self.buffer_summary = None

    def _ensure_column(self, column_name, default):
        if column_name not in self.df_steps.columns:
            self.df_steps[column_name] = default

    def load_data(self):
        if os.path.exists(self.detailed_csv):
            self.df_steps = pd.read_csv(self.detailed_csv)
            if "discovered_data" in self.df_steps.columns:
                self.df_steps["discovered_data"] = self.df_steps[
                    "discovered_data"
                ].apply(lambda x: json.loads(x) if pd.notna(x) and x else {})
            else:
                self.df_steps["discovered_data"] = pd.Series(
                    [{}] * len(self.df_steps), index=self.df_steps.index
                )

            self._ensure_column("alerts_count", 0)
            self._ensure_column("discovered_count", 0)
            self._ensure_column("success", 0)
            self._ensure_column("reward", 0)
            self._ensure_column("episode", range(1, len(self.df_steps) + 1))
            if (
                "attack_type" not in self.df_steps.columns
                and "attack_name" in self.df_steps.columns
            ):
                self.df_steps["attack_type"] = self.df_steps["attack_name"]
            self._ensure_column("attack_type", "unknown")
            self._ensure_column("params", "{}")
        else:
            raise FileNotFoundError(f"Missing {self.detailed_csv}")

        if os.path.exists(self.summary_json):
            with open(self.summary_json, "r") as f:
                data = json.load(f)
                self.summary_data = data[-1] if data else {}

        if os.path.exists(self.buffer_summary_json):
            with open(self.buffer_summary_json, "r") as f:
                self.buffer_summary = json.load(f)

    def generate_html_report(self):
        if self.df_steps is None:
            self.load_data()

        # إحصائيات سريعة
        total_steps = len(self.df_steps)
        success_rate = self.df_steps["success"].mean() * 100
        total_alerts = self.df_steps["alerts_count"].sum()
        avg_discovered = self.df_steps["discovered_count"].mean()

        # أكثر هجوم نجاحاً
        attack_stats = self.df_steps.groupby("attack_type")["success"].agg(
            ["sum", "count"]
        )
        attack_stats["success_rate"] = attack_stats["sum"] / attack_stats["count"] * 100
        best_attack = attack_stats["sum"].idxmax() if not attack_stats.empty else "N/A"
        best_attack_successes = (
            int(attack_stats.loc[best_attack, "sum"]) if best_attack != "N/A" else 0
        )
        best_attack_total = (
            int(attack_stats.loc[best_attack, "count"]) if best_attack != "N/A" else 0
        )

        # متوسط المكافآت والتنبؤات
        avg_reward = self.df_steps["reward"].mean()
        max_reward = self.df_steps["reward"].max()
        min_reward = self.df_steps["reward"].min()

        # تجميع البيانات المستخرجة عبر جميع الخطوات
        all_subdomains = set()
        all_ips = set()
        all_mx = set()
        all_ns = set()
        all_cnames = set()
        total_answers = 0

        for _, row in self.df_steps.iterrows():
            disc = row.get("discovered_data", {})
            if disc:
                all_subdomains.update(disc.get("subdomains", []))
                all_ips.update(disc.get("ip_addresses", []))
                all_mx.update(disc.get("mx_servers", []))
                all_ns.update(disc.get("ns_servers", []))
                all_cnames.update(disc.get("cnames", []))
                total_answers += disc.get("total_answers", 0)

        # رسم بياني: معدل النجاح حسب الخطوة
        fig_success = px.line(
            self.df_steps,
            x=self.df_steps.index,
            y="success",
            title="DNS Recon Success per Step",
            labels={"index": "Step", "success": "Success"},
        )

        # رسم بياني: عدد الاكتشافات
        fig_discovered = px.bar(
            self.df_steps,
            x=self.df_steps.index,
            y="discovered_count",
            title="Discovered Subdomains per Step",
            labels={"index": "Step"},
        )

        # رسم بياني: توزيع المكافآت
        fig_reward = px.histogram(
            self.df_steps, x="reward", nbins=30, title="Reward Distribution"
        )

        # رسم بياني: التنبيهات حسب الخطوة
        fig_alerts = px.line(
            self.df_steps,
            x=self.df_steps.index,
            y="alerts_count",
            title="IDS Alerts per Step",
            labels={"index": "Step"},
        )

        # بناء قسم البيانات المستخرجة بشكل منظم
        discovered_html = ""
        if all_subdomains or all_ips or all_mx or all_ns or all_cnames or total_answers:
            discovered_html = """
            <div style="background:#e8f5e8; padding:15px; border-radius:10px; margin:20px 0;">
                <h2 style="color:#2e7d32;"> Extracted Intelligence Summary</h2>
                <div style="display:flex; flex-wrap:wrap; gap:15px;">
            """
            if all_subdomains:
                discovered_html += f"""
                <div style="flex:1; min-width:200px;">
                    <h3> Subdomains ({len(all_subdomains)})</h3>
                    <ul style="max-height:200px; overflow-y:auto;">
                        {''.join(f'<li>{sub}</li>' for sub in sorted(all_subdomains)[:20])}
                        {f'<li>... and {len(all_subdomains)-20} more</li>' if len(all_subdomains) > 20 else ''}
                    </ul>
                </div>
                """
            if all_ips:
                discovered_html += f"""
                <div style="flex:1; min-width:200px;">
                    <h3> IP Addresses ({len(all_ips)})</h3>
                    <ul>{''.join(f'<li>{ip}</li>' for ip in sorted(all_ips)[:20])}</ul>
                </div>
                """
            if all_mx:
                discovered_html += f"""
                <div style="flex:1; min-width:200px;">
                    <h3> MX Servers ({len(all_mx)})</h3>
                    <ul>{''.join(f'<li>{mx}</li>' for mx in sorted(all_mx)[:20])}</ul>
                </div>
                """
            if all_ns:
                discovered_html += f"""
                <div style="flex:1; min-width:200px;">
                    <h3>🔧 NS Servers ({len(all_ns)})</h3>
                    <ul>{''.join(f'<li>{ns}</li>' for ns in sorted(all_ns)[:20])}</ul>
                </div>
                """
            if all_cnames:
                discovered_html += f"""
                <div style="flex:1; min-width:200px;">
                    <h3>🔗 CNAMEs ({len(all_cnames)})</h3>
                    <ul>{''.join(f'<li>{cname}</li>' for cname in sorted(all_cnames)[:20])}</ul>
                </div>
                """
            discovered_html += f"""
                </div>
                <p><strong> Total DNS Answers:</strong> {total_answers}</p>
            </div>
            """

        # عرض تفاصيل كل خطوة في جدول قابل للطي (تفاصيل إضافية)
        steps_details = ""
        for idx, row in self.df_steps.iterrows():
            disc = row.get("discovered_data", {})
            if disc and (
                disc.get("subdomains")
                or disc.get("ip_addresses")
                or disc.get("mx_servers")
                or disc.get("ns_servers")
                or disc.get("cnames")
            ):
                details_id = f"step_{idx}"
                steps_details += f"""
                <details style="margin-bottom:10px; border:1px solid #ddd; border-radius:8px; padding:10px;">
                    <summary style="font-weight:bold; cursor:pointer;">
                        Step {idx+1} (Episode {row['episode']}) - {row['attack_type']}
                    </summary>
                    <div style="margin-top:10px;">
                """
                if disc.get("subdomains"):
                    steps_details += f"<p><strong> Subdomains:</strong> {', '.join(disc['subdomains'])}</p>"
                if disc.get("ip_addresses"):
                    steps_details += f"<p><strong> IPs:</strong> {', '.join(disc['ip_addresses'])}</p>"
                if disc.get("mx_servers"):
                    steps_details += (
                        f"<p><strong> MX:</strong> {', '.join(disc['mx_servers'])}</p>"
                    )
                if disc.get("ns_servers"):
                    steps_details += (
                        f"<p><strong> NS:</strong> {', '.join(disc['ns_servers'])}</p>"
                    )
                if disc.get("cnames"):
                    steps_details += (
                        f"<p><strong> CNAMEs:</strong> {', '.join(disc['cnames'])}</p>"
                    )
                steps_details += f"<p><strong> Total Answers:</strong> {disc.get('total_answers',0)}</p>"
                steps_details += "</div></details>"

        if steps_details:
            steps_details = f"<h2> Per-Step Extracted Data</h2>{steps_details}"

        # تجميع HTML النهائي
        plotly_js = "https://cdn.plot.ly/plotly-latest.min.js"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DNS Recon RL Evaluation Report</title>
            <script src="{plotly_js}"></script>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 30px; background: #f0f2f5; }}
                .container {{ max-width: 1400px; margin: auto; background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
                .stats {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
                .card {{ background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); color: white; padding: 20px; border-radius: 12px; flex: 1; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .card h3 {{ margin: 0; font-size: 16px; opacity: 0.9; }}
                .card p {{ font-size: 28px; font-weight: bold; margin: 10px 0 0; }}
                .plot {{ margin-bottom: 35px; background: #f9f9ff; padding: 10px; border-radius: 12px; }}
                h1, h2 {{ color: #2c3e50; }}
                hr {{ margin: 30px 0; border: 0; height: 1px; background: #ddd; }}
                details {{ background: #fafafa; transition: all 0.2s; }}
                details:hover {{ background: #f0f0f0; }}
                summary {{ outline: none; }}
                code {{ background: #eee; padding: 2px 6px; border-radius: 4px; }}
            </style>
        </head>
        <body>
        <div class="container">
            <h1>🔍 DNS Reconnaissance Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <div class="stats">
                <div class="card"><h3>Total Steps</h3><p>{total_steps}</p></div>
                <div class="card"><h3>Success Rate</h3><p>{success_rate:.1f}%</p></div>
                <div class="card"><h3>Total Alerts</h3><p>{total_alerts}</p></div>
                <div class="card"><h3>Avg Discovered/Step</h3><p>{avg_discovered:.2f}</p></div>
            </div>
            <div class="stats" style="margin-top:0;">
                <div class="card" style="background: linear-gradient(135deg, #3498db, #2980b9);">
                    <h3> Most Successful Attack</h3>
                    <p>{best_attack}</p>
                    <div style="font-size:14px; margin-top:5px;">{best_attack_successes} successes out of {best_attack_total} attempts</div>
                </div>
                <div class="card" style="background: linear-gradient(135deg, #f39c12, #e67e22);">
                    <h3> Reward Stats</h3>
                    <p>Avg: {avg_reward:.2f}</p>
                    <div style="font-size:14px; margin-top:5px;">Max: {max_reward:.2f} | Min: {min_reward:.2f}</div>
                </div>
            </div>
            {discovered_html}
            <div class="plot">{fig_success.to_html(full_html=False, include_plotlyjs=False)}</div>
            <div class="plot">{fig_discovered.to_html(full_html=False, include_plotlyjs=False)}</div>
            <div class="plot">{fig_alerts.to_html(full_html=False, include_plotlyjs=False)}</div>
            <div class="plot">{fig_reward.to_html(full_html=False, include_plotlyjs=False)}</div>
            {steps_details}
            <hr>
            <h2> Summary Data</h2>
            <pre style="background:#f4f4f4; padding:10px; border-radius:8px;">{json.dumps(self.summary_data, indent=2) if self.summary_data else 'No summary data'}</pre>
            <h2> Buffer Summary</h2>
            <pre style="background:#f4f4f4; padding:10px; border-radius:8px;">{json.dumps(self.buffer_summary, indent=2) if self.buffer_summary else 'No buffer analysis found'}</pre>
        </div>
        </body>
        </html>
        """
        return html_content

    def generate_report(self, open_browser=True):
        html = self.generate_html_report()
        os.makedirs(self.result_dir, exist_ok=True)
        report_path = os.path.join(self.result_dir, "recon_evaluation_report.html")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html)
        if open_browser:
            webbrowser.open(f"file://{report_path}")
        print(f"[+] Recon report generated: {report_path}")
        return report_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", default=None)
    args = parser.parse_args()
    report = EvaluationReport(result_dir=args.result_dir)
    report.generate_report()
