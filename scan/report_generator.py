import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
        self.buffer_df = None
        self.model_knowledge = None

    def load_data(self):
        """Load all evaluation result files."""
        # Detailed steps
        if os.path.exists(self.detailed_csv):
            self.df_steps = pd.read_csv(self.detailed_csv)
            # Clean up port_results if exists
            if "port_results" in self.df_steps.columns:
                self.df_steps["port_results"] = self.df_steps["port_results"].fillna(
                    "[]"
                )
        else:
            raise FileNotFoundError(f"Missing {self.detailed_csv}")

        # Summary JSON
        if os.path.exists(self.summary_json):
            with open(self.summary_json, "r") as f:
                self.summary_data = json.load(f)
                if isinstance(self.summary_data, list):
                    self.summary_data = (
                        self.summary_data[-1] if self.summary_data else {}
                    )
        else:
            self.summary_data = {}

        # Buffer analysis CSV
        if os.path.exists(self.buffer_csv):
            self.buffer_df = pd.read_csv(self.buffer_csv)

        # Buffer summary JSON
        if os.path.exists(self.buffer_summary_json):
            with open(self.buffer_summary_json, "r") as f:
                self.buffer_summary = json.load(f)

        # Model knowledge JSON
        if os.path.exists(self.model_knowledge_json):
            with open(self.model_knowledge_json, "r") as f:
                self.model_knowledge = json.load(f)

    def _generate_buffer_summary_data(self):
        """Build buffer summary from step data when no JSON exists."""
        if self.buffer_summary is not None:
            return self.buffer_summary
        if self.df_steps is None:
            return {}

        attack_counts = self.df_steps.groupby("attack_type")["success"].agg(
            ["sum", "count"]
        )
        attack_counts["success_rate"] = (
            attack_counts["sum"] / attack_counts["count"] * 100
        )
        top_attacks = attack_counts.sort_values("sum", ascending=False).head(10)

        top_attacks_list = [
            {
                "attack_type": atk,
                "successes": int(row["sum"]),
                "attempts": int(row["count"]),
                "success_rate": round(row["success_rate"], 1),
            }
            for atk, row in top_attacks.iterrows()
        ]

        self.buffer_summary = {
            "total_steps": len(self.df_steps),
            "unique_attack_types": attack_counts.index.tolist(),
            "top_attacks": top_attacks_list,
        }
        try:
            with open(self.buffer_summary_json, "w") as f:
                json.dump(self.buffer_summary, f, indent=2)
        except Exception:
            pass
        return self.buffer_summary

    def _generate_best_attacks_by_category(self, categories=None):
        categories = categories or ["stealth", "fin", "ack", "window", "banner"]
        if self.df_steps is None or self.df_steps.empty:
            return "<p>No attack step data available.</p>"

        html = '<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">'
        for category in categories:
            matching = self.df_steps[
                self.df_steps["attack_type"]
                .astype(str)
                .str.lower()
                .str.contains(category)
            ]
            if matching.empty:
                html += f'<div class="bg-white rounded-lg shadow p-6"><h3 class="text-lg font-semibold text-gray-800 mb-3">{category.title()}</h3><p class="text-sm text-gray-600">No attacks found for this category.</p></div>'
                continue

            combo_df = matching.copy()
            combo_df["combo_str"] = (
                combo_df["attack_type"].astype(str)
                + ": "
                + combo_df["params"].astype(str)
            )
            combo_stats = combo_df.groupby("combo_str")["success"].agg(["sum", "count"])
            combo_stats["success_rate"] = (
                combo_stats["sum"] / combo_stats["count"] * 100
            )
            top_combos = combo_stats.sort_values("sum", ascending=False).head(3)

            rows = ""
            for combo, row in top_combos.iterrows():
                rows += f'<li class="text-sm text-gray-700 mb-2"><strong>{combo}</strong> — {int(row["sum"])} successes / {int(row["count"])} attempts ({row["success_rate"]:.1f}% success)</li>'

            html += f"""
            <div class=\"bg-white rounded-lg shadow p-6\">
                <h3 class=\"text-lg font-semibold text-gray-800 mb-3\">{category.title()}</h3>
                <p class=\"text-sm text-gray-600 mb-4\">Found {len(matching)} matching rows.</p>
                <ul class=\"list-disc list-inside\">{rows}</ul>
            </div>
            """
        html += "</div>"
        return html

    def _generate_buffer_summary_html(self):
        summary = self.buffer_summary or self._generate_buffer_summary_data()
        if not summary:
            return "<p>No buffer summary available.</p>"

        top_attacks_html = ""
        for item in summary.get("top_attacks", []):
            top_attacks_html += (
                f'<li class="text-sm text-gray-700 mb-2">'
                f"<strong>{item['attack_type']}</strong>: {item['successes']} successes "
                f"out of {item['attempts']} attempts ({item['success_rate']}%)</li>"
            )

        unique_types = summary.get("unique_attack_types", [])
        return f"""
        <div class=\"bg-white rounded-lg shadow p-6 mb-8\">
            <h2 class=\"text-2xl font-bold text-gray-800 mb-4\">Buffer Summary</h2>
            <p class=\"text-sm text-gray-600 mb-4\">Total steps in buffer: {summary.get('total_steps', 0)}</p>
            <p class=\"text-sm text-gray-600 mb-4\">Unique attack types in buffer: {len(unique_types)}</p>
            <div class=\"mb-4\"><strong>Attack types:</strong> {', '.join(unique_types[:20])}</div>
            <div>
                <h3 class=\"text-lg font-semibold text-gray-800 mb-2\">Top Buffer Attacks</h3>
                <ul class=\"list-disc list-inside\">{top_attacks_html}</ul>
            </div>
        </div>
        """

    def _generate_stats_cards(self):
        """Return HTML for stats cards."""
        total_steps = len(self.df_steps) if self.df_steps is not None else 0
        success_rate = (
            self.df_steps["success"].mean() * 100 if self.df_steps is not None else 0
        )
        total_alerts = (
            self.df_steps["alerts_count"].sum() if self.df_steps is not None else 0
        )
        # Best attack type
        if self.df_steps is not None:
            attack_success = self.df_steps.groupby("attack_type")["success"].mean()
            best_attack = attack_success.idxmax() if not attack_success.empty else "N/A"
            best_rate = attack_success.max() * 100 if not attack_success.empty else 0

            # Reward statistics
            avg_reward = self.df_steps["reward"].mean()
            max_reward = self.df_steps["reward"].max()
            min_reward = self.df_steps["reward"].min()
        else:
            best_attack = "N/A"
            best_rate = 0
            avg_reward = max_reward = min_reward = 0

        cards = f"""
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="bg-white rounded-lg shadow p-6 border-l-8 border-blue-500">
                <div class="text-sm font-medium text-gray-500">Total Steps</div>
                <div class="text-3xl font-bold text-gray-800">{total_steps}</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6 border-l-8 border-green-500">
                <div class="text-sm font-medium text-gray-500">Overall Success Rate</div>
                <div class="text-3xl font-bold text-gray-800">{success_rate:.1f}%</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6 border-l-8 border-red-500">
                <div class="text-sm font-medium text-gray-500">Total Alerts Triggered</div>
                <div class="text-3xl font-bold text-gray-800">{total_alerts}</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6 border-l-8 border-purple-500">
                <div class="text-sm font-medium text-gray-500">Best Attack Type (Rate)</div>
                <div class="text-3xl font-bold text-gray-800">{best_attack} ({best_rate:.0f}%)</div>
            </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-white rounded-lg shadow p-6 border-l-8 border-yellow-500">
                <div class="text-sm font-medium text-gray-500">Average Reward</div>
                <div class="text-3xl font-bold text-gray-800">{avg_reward:.2f}</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6 border-l-8 border-green-500">
                <div class="text-sm font-medium text-gray-500">Max Reward</div>
                <div class="text-3xl font-bold text-gray-800">{max_reward:.2f}</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6 border-l-8 border-red-500">
                <div class="text-sm font-medium text-gray-500">Min Reward</div>
                <div class="text-3xl font-bold text-gray-800">{min_reward:.2f}</div>
            </div>
        </div>
        """
        return cards

    def _generate_success_details(self):
        """Generate detailed success stats: best attack, parameter combinations ranking."""
        if self.df_steps is None or self.df_steps.empty:
            return "<p>No step data available.</p>"

        # 1. Most successful attack type (by number of successes, not rate)
        attack_counts = self.df_steps.groupby("attack_type")["success"].agg(
            ["sum", "count"]
        )
        attack_counts["success_rate"] = (
            attack_counts["sum"] / attack_counts["count"] * 100
        )
        attack_counts = attack_counts.sort_values("sum", ascending=False)

        best_attack = attack_counts.iloc[0]["sum"]
        best_attack_name = attack_counts.index[0]
        best_attack_success_count = int(best_attack)
        best_attack_total = int(attack_counts.iloc[0]["count"])

        # 2. Parameter combinations ranking (most exploited)
        param_combos = self.df_steps.copy()
        # Convert params dict to a readable string
        param_combos["combo_str"] = param_combos.apply(
            lambda row: f"{row['attack_type']} -> {row['params']}", axis=1
        )
        combo_stats = param_combos.groupby("combo_str")["success"].agg(["sum", "count"])
        combo_stats["success_rate"] = combo_stats["sum"] / combo_stats["count"] * 100
        # Most exploited (highest number of successes)
        most_exploited = combo_stats.sort_values("sum", ascending=False).head(10)
        # Least exploited (lowest number of successes, but only consider combos that occurred at least once)
        least_exploited = combo_stats.sort_values("sum", ascending=True).head(10)

        # Attack stats list for the second card
        attack_stats_list = ""
        for atk in attack_counts.head(5).index:
            row = attack_counts.loc[atk]
            attack_stats_list += f'<li class="flex justify-between items-center"><span class="font-medium">{atk}</span><span>{int(row["sum"])}/{int(row["count"])} successes</span></li>'

        # Most exploited rows
        most_rows = ""
        for idx, (combo, row) in enumerate(most_exploited.iterrows(), 1):
            display_combo = combo if len(combo) <= 80 else combo[:77] + "..."
            most_rows += f"""
            <tr class="hover:bg-gray-50">
                <td class="px-4 py-2 text-sm text-gray-600">{idx}</td>
                <td class="px-4 py-2 text-sm font-mono text-gray-700">{display_combo}</td>
                <td class="px-4 py-2 text-sm text-center text-green-600 font-semibold">{int(row['sum'])}</td>
                <td class="px-4 py-2 text-sm text-center">{int(row['count'])}</td>
                <td class="px-4 py-2 text-sm text-center">{row['success_rate']:.1f}%</td>
            </tr>
            """

        # Least exploited rows
        least_rows = ""
        for idx, (combo, row) in enumerate(least_exploited.iterrows(), 1):
            display_combo = combo if len(combo) <= 80 else combo[:77] + "..."
            least_rows += f"""
            <tr class="hover:bg-gray-50">
                <td class="px-4 py-2 text-sm text-gray-600">{idx}</td>
                <td class="px-4 py-2 text-sm font-mono text-gray-700">{display_combo}</td>
                <td class="px-4 py-2 text-sm text-center text-red-500">{int(row['sum'])}</td>
                <td class="px-4 py-2 text-sm text-center">{int(row['count'])}</td>
                <td class="px-4 py-2 text-sm text-center">{row['success_rate']:.1f}%</td>
            </tr>
            """

        html = f"""
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <!-- Most Successful Attack -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-bold text-gray-800 mb-4 flex items-center">
                     Most Successful Attack Type
                </h3>
                <div class="text-center">
                    <div class="text-4xl font-bold text-green-600">{best_attack_name}</div>
                    <div class="text-2xl font-semibold text-gray-700 mt-2">{best_attack_success_count} successes</div>
                    <div class="text-gray-500">out of {best_attack_total} attempts</div>
                </div>
            </div>
            
            <!-- Quick Stats -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-bold text-gray-800 mb-4"> Success Snapshot</h3>
                <ul class="space-y-2">
                    {attack_stats_list}
                </ul>
            </div>
        </div>
        
        <!-- Most Exploited Parameter Combinations -->
        <div class="bg-white rounded-lg shadow p-6 mb-8">
            <h3 class="text-xl font-bold text-gray-800 mb-4"> Top 10 Most Exploited Attack+Param Combinations</h3>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Rank</th>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Attack + Parameters</th>
                            <th class="px-4 py-2 text-center text-xs font-medium text-gray-500">Successes</th>
                            <th class="px-4 py-2 text-center text-xs font-medium text-gray-500">Attempts</th>
                            <th class="px-4 py-2 text-center text-xs font-medium text-gray-500">Success Rate</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200">
                        {most_rows}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Least Exploited Parameter Combinations -->
        <div class="bg-white rounded-lg shadow p-6 mb-8">
            <h3 class="text-xl font-bold text-gray-800 mb-4"> Top 10 Least Exploited Attack+Param Combinations</h3>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Rank</th>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Attack + Parameters</th>
                            <th class="px-4 py-2 text-center text-xs font-medium text-gray-500">Successes</th>
                            <th class="px-4 py-2 text-center text-xs font-medium text-gray-500">Attempts</th>
                            <th class="px-4 py-2 text-center text-xs font-medium text-gray-500">Success Rate</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200">
                        {least_rows}
                    </tbody>
                </table>
            </div>
        </div>
        """
        return html

    def _generate_plots_html(self):
        """Generate Plotly figures as HTML divs."""
        if self.df_steps is None:
            return "<p>No step data available.</p>"

        # 1. Success Rate by Attack Type
        attack_success = (
            self.df_steps.groupby("attack_type")["success"].mean().reset_index()
        )
        fig1 = px.bar(
            attack_success,
            x="attack_type",
            y="success",
            title="Success Rate by Attack Type",
            labels={"success": "Success Rate", "attack_type": "Attack Type"},
            color="success",
            color_continuous_scale="Viridis",
        )
        fig1.update_layout(plot_bgcolor="white", height=400)

        # 2. Reward Distribution Boxplot
        fig2 = px.box(
            self.df_steps,
            x="attack_type",
            y="reward",
            title="Reward Distribution per Attack",
            labels={"reward": "Reward", "attack_type": "Attack Type"},
            color="attack_type",
        )
        fig2.update_layout(plot_bgcolor="white", height=400)

        # 3. Success Trend over Episodes
        ep_success = self.df_steps.groupby("episode")["success"].mean().reset_index()
        fig3 = px.line(
            ep_success,
            x="episode",
            y="success",
            title="Success Rate per Episode (Rolling Average)",
            labels={"success": "Success Rate", "episode": "Episode"},
        )
        fig3.update_layout(plot_bgcolor="white", height=400)

        # 4. Alerts per Episode
        ep_alerts = self.df_steps.groupby("episode")["alerts_count"].sum().reset_index()
        fig4 = px.bar(
            ep_alerts,
            x="episode",
            y="alerts_count",
            title="Total Alerts per Episode",
            labels={"alerts_count": "Alerts", "episode": "Episode"},
            color="alerts_count",
            color_continuous_scale="Reds",
        )
        fig4.update_layout(plot_bgcolor="white", height=400)

        # 5. Alerts per Step
        fig5 = px.line(
            self.df_steps,
            x=self.df_steps.index,
            y="alerts_count",
            title="IDS Alerts per Step",
            labels={"index": "Step", "alerts_count": "Alerts"},
        )
        fig5.update_layout(plot_bgcolor="white", height=400)

        # 6. Buffer Attack Distribution (if available)
        fig6 = None
        if self.buffer_df is not None:
            buffer_counts = self.buffer_df["attack_type"].value_counts().reset_index()
            buffer_counts.columns = ["attack_type", "count"]
            fig6 = px.pie(
                buffer_counts,
                values="count",
                names="attack_type",
                title="Attack Distribution in Replay Buffer",
                hole=0.3,
            )
            fig6.update_layout(height=400)

        plots_html = fig1.to_html(full_html=False, include_plotlyjs="cdn")
        plots_html += fig2.to_html(full_html=False, include_plotlyjs=False)
        plots_html += fig3.to_html(full_html=False, include_plotlyjs=False)
        plots_html += fig4.to_html(full_html=False, include_plotlyjs=False)
        plots_html += fig5.to_html(full_html=False, include_plotlyjs=False)
        if fig6:
            plots_html += fig6.to_html(full_html=False, include_plotlyjs=False)

        return plots_html

    def _generate_table_html(self):
        """Generate interactive HTML table with filtering."""
        if self.df_steps is None:
            return "<p>No data for table.</p>"

        # Convert dataframe to JSON for JavaScript
        records = self.df_steps.to_dict(orient="records")
        data_json = json.dumps(records)

        table_html = f"""
        <div class="bg-white rounded-lg shadow overflow-hidden mb-8">
            <div class="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <h3 class="text-lg font-semibold text-gray-800">Detailed Evaluation Steps</h3>
                <div class="mt-2 flex flex-wrap gap-4">
                    <input type="text" id="searchInput" placeholder="Search anything..." class="px-3 py-2 border border-gray-300 rounded-md text-sm w-64">
                    <select id="filterAttack" class="px-3 py-2 border border-gray-300 rounded-md text-sm">
                        <option value="">All Attacks</option>
                        {''.join(f'<option value="{atk}">{atk}</option>' for atk in self.df_steps['attack_type'].unique())}
                    </select>
                    <select id="filterSuccess" class="px-3 py-2 border border-gray-300 rounded-md text-sm">
                        <option value="">Success Status</option>
                        <option value="true">Success</option>
                        <option value="false">Failed</option>
                    </select>
                    <input type="number" id="filterMinAlerts" placeholder="Min Alerts" class="px-3 py-2 border border-gray-300 rounded-md text-sm w-32">
                    <button id="resetFilters" class="px-4 py-2 bg-gray-600 text-white rounded-md text-sm">Reset Filters</button>
                </div>
            </div>
            <div class="overflow-x-auto">
                <table id="stepsTable" class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Episode</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Step</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Attack</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Params</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Success</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Alerts</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reward</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration(s)</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody"></tbody>
                </table>
            </div>
            <div class="px-6 py-3 bg-gray-50 border-t border-gray-200" id="tableInfo"></div>
        </div>

        <script>
        const allData = {data_json};
        const attackSelect = document.getElementById('filterAttack');
        const successSelect = document.getElementById('filterSuccess');
        const searchInput = document.getElementById('searchInput');
        const minAlertsInput = document.getElementById('filterMinAlerts');
        const resetBtn = document.getElementById('resetFilters');
        const tbody = document.getElementById('tableBody');
        const tableInfo = document.getElementById('tableInfo');

        function renderTable(data) {{
            tbody.innerHTML = '';
            if (data.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-gray-500">No rows match filters</td></tr>';
                tableInfo.innerText = 'Showing 0 of 0 entries';
                return;
            }}
            data.forEach(row => {{
                let tr = document.createElement('tr');
                tr.className = 'hover:bg-gray-50';
                tr.innerHTML = `
                    <td class="px-6 py-3 text-sm text-gray-700">${{row.episode}}</td>
                    <td class="px-6 py-3 text-sm text-gray-700">${{row.step}}</td>
                    <td class="px-6 py-3 text-sm font-medium text-gray-900">${{row.attack_type}}</td>
                    <td class="px-6 py-3 text-sm text-gray-500"><code class="bg-gray-100 px-1 rounded">${{JSON.stringify(row.params).substring(0, 140)}}</code></td>
                    <td class="px-6 py-3 text-sm">${{row.success ? '<span class="text-green-600 font-semibold">✓</span>' : '<span class="text-red-600">✗</span>'}}</td>
                    <td class="px-6 py-3 text-sm text-gray-700">${{row.alerts_count}}</td>
                    <td class="px-6 py-3 text-sm text-gray-700">${{row.reward}}</td>
                    <td class="px-6 py-3 text-sm text-gray-700">${{row.duration}}</td>
                `;
                tbody.appendChild(tr);
            }});
            tableInfo.innerText = `Showing ${{data.length}} of ${{allData.length}} entries`;
        }}

        function applyFilters() {{
            let filtered = [...allData];
            const attackVal = attackSelect.value;
            if (attackVal) filtered = filtered.filter(r => r.attack_type === attackVal);
            const successVal = successSelect.value;
            if (successVal !== '') filtered = filtered.filter(r => r.success === (successVal === 'true'));
            const searchTerm = searchInput.value.toLowerCase();
            if (searchTerm) {{
                filtered = filtered.filter(r => 
                    r.attack_type.toLowerCase().includes(searchTerm) ||
                    JSON.stringify(r.params).toLowerCase().includes(searchTerm) ||
                    r.episode.toString().includes(searchTerm)
                );
            }}
            const minAlerts = parseInt(minAlertsInput.value);
            if (!isNaN(minAlerts)) filtered = filtered.filter(r => r.alerts_count >= minAlerts);
            renderTable(filtered);
        }}

        attackSelect.addEventListener('change', applyFilters);
        successSelect.addEventListener('change', applyFilters);
        searchInput.addEventListener('input', applyFilters);
        minAlertsInput.addEventListener('input', applyFilters);
        resetBtn.addEventListener('click', () => {{
            attackSelect.value = '';
            successSelect.value = '';
            searchInput.value = '';
            minAlertsInput.value = '';
            applyFilters();
        }});
        applyFilters();
        </script>
        """
        return table_html

    def generate_report(self, open_browser=True):
        """Generate full HTML report and optionally open in browser."""
        self.load_data()
        stats_html = self._generate_stats_cards()
        success_details_html = self._generate_success_details()
        plots_html = self._generate_plots_html()
        table_html = self._generate_table_html()

        category_highlights_html = self._generate_best_attacks_by_category(
            ["stealth", "fin", "ack", "window", "banner"]
        )
        buffer_summary_html = self._generate_buffer_summary_html()

        full_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Cyber RL Evaluation Report</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ background-color: #f3f4f6; }}
                .container {{ max-width: 1400px; }}
            </style>
        </head>
        <body class="bg-gray-100">
            <div class="container mx-auto px-4 py-8">
                <div class="bg-white rounded-lg shadow-md p-6 mb-8">
                    <h1 class="text-3xl font-bold text-gray-800">🎯 Cyber RL Evaluation Report</h1>
                    <p class="text-gray-500 mt-1">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p class="text-sm text-gray-500">Target: {self.summary_data.get('target_ip', 'N/A')} | Episodes: {self.summary_data.get('total_episodes', 'N/A')}</p>
                </div>

                {stats_html}
                {success_details_html}

                <div class="bg-white rounded-lg shadow p-6 mb-8">
                    <h2 class="text-xl font-semibold text-gray-800 mb-4">📊 Performance Analytics</h2>
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <div>{plots_html.split('<div>')[1] if '<div>' in plots_html else plots_html}</div>
                    </div>
                </div>

                <div>
                    {table_html}
                </div>

                <div class="text-center text-gray-400 text-sm mt-8">
                    Report generated by EvaluationReport tool • Data from {self.result_dir}
                </div>
            </div>
        </body>
        </html>
        """

        os.makedirs(self.result_dir, exist_ok=True)
        report_path = os.path.join(self.result_dir, "scan_evaluation_report.html")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        if open_browser:
            webbrowser.open(f"file://{report_path}")
        print(f"[+] Scan report generated and opened in browser. File: {report_path}")
        return report_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Professional Evaluation Report"
    )
    parser.add_argument(
        "--result-dir",
        default=None,
        help="Directory containing evaluation result files",
    )
    args = parser.parse_args()

    report = EvaluationReport(result_dir=args.result_dir)
    report.generate_report(open_browser=True)
