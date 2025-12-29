"""
Enhanced AI Chatbot Engine for Performance Analysis
Provides intelligent responses based on performance metrics
"""
from typing import List, Dict, Any
import json
import re

class PerformanceChatbot:
    """Advanced chatbot for analyzing performance test results"""
    
    # Comprehensive sample prompts organized by category
    SAMPLE_PROMPTS = {
        "overview": [
            "Give me an overview of the test results",
            "What's the overall performance grade?",
            "How did the system perform overall?",
            "Summarize the test results",
            "What's the executive summary?",
        ],
        "response_times": [
            "What are the response times?",
            "Show me the average response time",
            "What's the 95th percentile response time?",
            "Which endpoints are the slowest?",
            "What's the median response time?",
            "Show me all percentile data (70th, 80th, 90th, 95th, 99th)",
        ],
        "errors": [
            "What's the error rate?",
            "Show me all errors",
            "Which endpoints have the most errors?",
            "What types of errors occurred?",
            "How many requests failed?",
            "What's the success rate?",
        ],
        "performance_issues": [
            "What are the critical issues?",
            "What problems were identified?",
            "What's causing poor performance?",
            "Which endpoints need optimization?",
            "What are the bottlenecks?",
            "What's failing or slow?",
        ],
        "recommendations": [
            "How can I improve performance?",
            "What are your recommendations?",
            "How do I fix these issues?",
            "What should I optimize first?",
            "What's the action plan?",
            "How do I achieve A+ grade?",
        ],
        "comparisons": [
            "How does this compare to industry standards?",
            "Are we meeting SLA requirements?",
            "Compare current vs target metrics",
            "What metrics are below target?",
            "What metrics are passing?",
        ],
        "business_impact": [
            "What's the business impact?",
            "How does this affect users?",
            "What's the cost of these issues?",
            "What's the ROI of fixing this?",
            "How does performance affect revenue?",
        ],
        "specific_metrics": [
            "What's the throughput?",
            "Show me SLA compliance",
            "What's the availability?",
            "How many requests were tested?",
            "What was the test duration?",
            "Show me transaction statistics",
        ],
        "trends": [
            "Show me the worst performing transactions",
            "What are the top 10 slowest endpoints?",
            "Which requests have high error rates?",
            "Show me performance breakdown by endpoint",
        ],
    }
    
    @staticmethod
    def get_sample_prompts() -> Dict[str, List[str]]:
        """Get all sample prompts organized by category"""
        return PerformanceChatbot.SAMPLE_PROMPTS
    
    @staticmethod
    def get_random_prompts(count: int = 6) -> List[str]:
        """Get random sample prompts for quick access"""
        import random
        all_prompts = []
        for category_prompts in PerformanceChatbot.SAMPLE_PROMPTS.values():
            all_prompts.extend(category_prompts)
        return random.sample(all_prompts, min(count, len(all_prompts)))
    
    @staticmethod
    def analyze_query_intent(message: str) -> str:
        """Determine the intent of the user's query"""
        message_lower = message.lower()
        
        # Intent keywords mapping
        intent_keywords = {
            "overview": ["overview", "summary", "overall", "general", "executive", "report"],
            "grade": ["grade", "score", "rating", "assessment"],
            "response_time": ["response", "latency", "time", "speed", "slow", "fast", "percentile"],
            "error": ["error", "fail", "failure", "problem", "issue", "bug"],
            "throughput": ["throughput", "rps", "requests per second", "volume", "load"],
            "availability": ["availability", "uptime", "downtime", "success rate"],
            "sla": ["sla", "compliance", "meet", "target", "requirement"],
            "recommendation": ["recommend", "suggest", "improve", "fix", "optimize", "enhance", "better"],
            "critical": ["critical", "urgent", "important", "priority", "severe"],
            "comparison": ["compare", "vs", "versus", "difference", "benchmark", "standard"],
            "business": ["business", "impact", "revenue", "cost", "roi", "user"],
            "endpoint": ["endpoint", "api", "transaction", "request", "url"],
            "specific_metric": ["median", "average", "mean", "max", "min", "p95", "p99", "70th", "80th", "90th"],
        }
        
        # Check for intent
        for intent, keywords in intent_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent
        
        return "general"
    
    @staticmethod
    def generate_response(message: str, context_data: List[Dict]) -> str:
        """
        Generate intelligent AI response based on message and context
        
        Args:
            message: User's question
            context_data: List of analyzed file data with metrics
            
        Returns:
            Comprehensive response string
        """
        if not context_data:
            return PerformanceChatbot._no_context_response()
        
        intent = PerformanceChatbot.analyze_query_intent(message)
        
        # Route to appropriate handler
        if intent == "overview":
            return PerformanceChatbot._generate_overview_response(context_data)
        elif intent == "grade":
            return PerformanceChatbot._generate_grade_response(context_data)
        elif intent == "response_time":
            return PerformanceChatbot._generate_response_time_analysis(context_data)
        elif intent == "error":
            return PerformanceChatbot._generate_error_analysis(context_data)
        elif intent == "throughput":
            return PerformanceChatbot._generate_throughput_analysis(context_data)
        elif intent == "availability":
            return PerformanceChatbot._generate_availability_analysis(context_data)
        elif intent == "sla":
            return PerformanceChatbot._generate_sla_analysis(context_data)
        elif intent == "recommendation":
            return PerformanceChatbot._generate_recommendations(context_data)
        elif intent == "critical":
            return PerformanceChatbot._generate_critical_issues(context_data)
        elif intent == "comparison":
            return PerformanceChatbot._generate_comparison(context_data)
        elif intent == "business":
            return PerformanceChatbot._generate_business_impact(context_data)
        elif intent == "endpoint":
            return PerformanceChatbot._generate_endpoint_analysis(context_data)
        elif intent == "specific_metric":
            return PerformanceChatbot._generate_specific_metrics(context_data, message)
        else:
            return PerformanceChatbot._generate_general_response(context_data, message)
    
    @staticmethod
    def _no_context_response() -> str:
        """Response when no analyzed files are available"""
        return """🤖 **No Analysis Data Available**

I need analyzed files to provide insights. Here's how to get started:

1️⃣ **Upload Files**: Go to Upload page and upload your JMeter/performance test files
2️⃣ **Analyze**: Go to Analysis page and analyze the uploaded files
3️⃣ **Ask Questions**: Come back and ask me anything about your results!

**Example questions you can ask:**
• What's the overall performance grade?
• Show me the error rates
• What are the response times?
• Give me recommendations for improvement
• What are the critical issues?

I'm here to help you understand your performance test results! 🚀"""
    
    @staticmethod
    def _generate_overview_response(context_data: List[Dict]) -> str:
        """Generate comprehensive overview"""
        responses = ["📊 **Performance Test Results Overview**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            category = data.get("category", "unknown")
            metrics = data.get("metrics", {})
            
            if category == "jmeter":
                summary = metrics.get("summary", {})
                grade = summary.get("overall_grade", "N/A")
                score = summary.get("overall_score", 0)
                success_rate = summary.get("success_rate", 0)
                
                sample_time = metrics.get("sample_time", {})
                avg_time = sample_time.get("mean", 0) / 1000
                p95 = sample_time.get("p95", 0) / 1000
                
                error_rate = metrics.get("error_rate", 0) * 100
                throughput = metrics.get("throughput", 0)
                total_samples = metrics.get("total_samples", 0)
                
                responses.append(f"""
**📁 {filename}**

🎯 **Overall Grade:** {grade} ({score:.0f}/100)
✅ **Success Rate:** {success_rate:.1f}%
⚡ **Avg Response:** {avg_time:.2f}s
📈 **95th Percentile:** {p95:.2f}s
❌ **Error Rate:** {error_rate:.2f}%
🔄 **Throughput:** {throughput:.1f} req/s
📊 **Total Requests:** {total_samples:,}

**Grade Breakdown:**
""")
                
                grade_reasons = summary.get("grade_reasons", {})
                for category_name, display_name in [
                    ("performance", "⚡ Performance"),
                    ("reliability", "🛡️ Reliability"),
                    ("user_experience", "👥 User Experience"),
                    ("scalability", "📈 Scalability")
                ]:
                    gr = grade_reasons.get(category_name, {})
                    responses.append(f"• {display_name}: **{gr.get('grade', 'N/A')}** - {gr.get('reason', 'N/A')}")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_grade_response(context_data: List[Dict]) -> str:
        """Generate detailed grade analysis"""
        responses = ["🎯 **Performance Grade Analysis**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            metrics = data.get("metrics", {})
            summary = metrics.get("summary", {})
            
            grade = summary.get("overall_grade", "N/A")
            score = summary.get("overall_score", 0)
            scores = summary.get("scores", {})
            
            responses.append(f"""
**📁 {filename}**

**Overall Grade: {grade}** ({score:.0f}/100)

**Detailed Scores:**
• ⚡ Performance: {scores.get('performance', 0):.0f}/100
• 🛡️ Reliability: {scores.get('reliability', 0):.0f}/100
• 👥 User Experience: {scores.get('user_experience', 0):.0f}/100
• 📈 Scalability: {scores.get('scalability', 0):.0f}/100

**Score Breakdown:**
• Availability: {scores.get('availability', 0):.0f}/100
• Response Time: {scores.get('response_time', 0):.0f}/100
• Error Rate: {scores.get('error_rate', 0):.0f}/100
• Throughput: {scores.get('throughput', 0):.0f}/100
• 95th Percentile: {scores.get('p95_percentile', 0):.0f}/100
• SLA Compliance: {scores.get('sla_compliance', 0):.0f}/100

**Grading Scale:**
• A+ (90-100): Exceptional
• A (80-89): Excellent
• B+ (75-79): Good
• B (70-74): Acceptable
• C+ (65-69): Marginal ← Current: {grade}
• D (50-59): Critical
""")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_response_time_analysis(context_data: List[Dict]) -> str:
        """Generate response time analysis"""
        responses = ["⚡ **Response Time Analysis**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            metrics = data.get("metrics", {})
            sample_time = metrics.get("sample_time", {})
            
            responses.append(f"""
**📁 {filename}**

**Response Time Statistics:**
• Minimum: {sample_time.get('min', 0)/1000:.2f}s
• Median: {sample_time.get('median', 0)/1000:.2f}s
• Average: {sample_time.get('mean', 0)/1000:.2f}s
• 70th Percentile: {sample_time.get('p70', 0)/1000:.2f}s
• 80th Percentile: {sample_time.get('p80', 0)/1000:.2f}s
• 90th Percentile: {sample_time.get('p90', 0)/1000:.2f}s
• 95th Percentile: {sample_time.get('p95', 0)/1000:.2f}s
• 99th Percentile: {sample_time.get('p99', 0)/1000:.2f}s
• Maximum: {sample_time.get('max', 0)/1000:.2f}s

**Analysis:**
""")
            
            avg = sample_time.get('mean', 0) / 1000
            p95 = sample_time.get('p95', 0) / 1000
            
            if avg < 1:
                responses.append("✅ Excellent average response time!")
            elif avg < 2:
                responses.append("✅ Good average response time, meets SLA")
            elif avg < 5:
                responses.append("⚠️ Average response time needs improvement")
            else:
                responses.append("❌ Critical: Response time is too slow")
            
            if p95 < 3:
                responses.append("✅ 95th percentile is within acceptable range")
            else:
                responses.append("⚠️ 95th percentile indicates some slow requests")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_error_analysis(context_data: List[Dict]) -> str:
        """Generate error rate analysis"""
        responses = ["❌ **Error Rate Analysis**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            metrics = data.get("metrics", {})
            
            error_rate = metrics.get("error_rate", 0) * 100
            total_errors = metrics.get("total_errors", 0)
            total_samples = metrics.get("total_samples", 0)
            response_codes = metrics.get("response_codes", {})
            
            responses.append(f"""
**📁 {filename}**

**Error Statistics:**
• Total Errors: {total_errors:,}
• Total Requests: {total_samples:,}
• Error Rate: {error_rate:.2f}%
• Success Rate: {100-error_rate:.2f}%

**Response Code Distribution:**
""")
            
            for code, count in sorted(response_codes.items(), key=lambda x: x[1], reverse=True)[:10]:
                percentage = (count / total_samples * 100) if total_samples > 0 else 0
                status = "✅" if code.startswith("2") else "⚠️" if code.startswith("4") else "❌"
                responses.append(f"{status} {code}: {count:,} ({percentage:.2f}%)")
            
            responses.append("\n**Analysis:**")
            if error_rate < 0.5:
                responses.append("✅ Excellent error rate!")
            elif error_rate < 1:
                responses.append("✅ Good error rate, within acceptable limits")
            elif error_rate < 3:
                responses.append("⚠️ Error rate needs attention")
            else:
                responses.append("❌ Critical: High error rate affecting reliability")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_recommendations(context_data: List[Dict]) -> str:
        """Generate recommendations"""
        responses = ["💡 **Performance Improvement Recommendations**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            metrics = data.get("metrics", {})
            summary = metrics.get("summary", {})
            recommendations = summary.get("recommendations", [])
            
            responses.append(f"**📁 {filename}**\n")
            
            if recommendations:
                for rec in recommendations:
                    category = rec.get("category", "General")
                    priority = rec.get("priority", "Medium")
                    items = rec.get("items", [])
                    
                    responses.append(f"\n**{category}** (Priority: {priority})")
                    for item in items[:5]:
                        responses.append(f"• {item}")
            else:
                responses.append("✅ No specific recommendations - system performing well!")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_critical_issues(context_data: List[Dict]) -> str:
        """Generate critical issues analysis"""
        responses = ["🔴 **Critical Issues Identified**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            metrics = data.get("metrics", {})
            summary = metrics.get("summary", {})
            critical_issues = summary.get("critical_issues", [])
            
            responses.append(f"**📁 {filename}**\n")
            
            if critical_issues:
                for i, issue in enumerate(critical_issues, 1):
                    responses.append(f"""
**Issue #{i}: {issue.get('title', 'Unknown')}**
• **Impact:** {issue.get('impact', 'N/A')}
• **Affected:** {issue.get('affected', 'N/A')}
• **Priority:** {issue.get('priority', 'N/A')}
• **Timeline:** {issue.get('timeline', 'N/A')}
""")
            else:
                responses.append("✅ No critical issues identified!")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_sla_analysis(context_data: List[Dict]) -> str:
        """Generate SLA compliance analysis"""
        responses = ["📊 **SLA Compliance Analysis**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            metrics = data.get("metrics", {})
            summary = metrics.get("summary", {})
            
            sla_2s = summary.get("sla_compliance_2s", 0)
            sla_3s = summary.get("sla_compliance_3s", 0)
            sla_5s = summary.get("sla_compliance_5s", 0)
            
            responses.append(f"""
**📁 {filename}**

**SLA Compliance:**
• ≤ 2 seconds: {sla_2s:.1f}% {'✅' if sla_2s >= 95 else '⚠️' if sla_2s >= 80 else '❌'}
• ≤ 3 seconds: {sla_3s:.1f}% {'✅' if sla_3s >= 95 else '⚠️' if sla_3s >= 80 else '❌'}
• ≤ 5 seconds: {sla_5s:.1f}% {'✅' if sla_5s >= 95 else '⚠️' if sla_5s >= 80 else '❌'}

**Target:** >95% compliance
**Status:** {'Meeting SLA ✅' if sla_2s >= 95 else 'Below SLA ⚠️' if sla_2s >= 80 else 'Critical SLA Violation ❌'}
""")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_throughput_analysis(context_data: List[Dict]) -> str:
        """Generate throughput analysis"""
        responses = ["🔄 **Throughput Analysis**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            metrics = data.get("metrics", {})
            
            throughput = metrics.get("throughput", 0)
            total_samples = metrics.get("total_samples", 0)
            summary = metrics.get("summary", {})
            duration = summary.get("test_duration_hours", 0)
            
            responses.append(f"""
**📁 {filename}**

**Throughput Metrics:**
• Throughput: {throughput:.1f} requests/second
• Total Requests: {total_samples:,}
• Test Duration: {duration:.2f} hours
• Avg per Hour: {total_samples/duration if duration > 0 else 0:,.0f}

**Analysis:**
""")
            
            if throughput >= 150:
                responses.append("✅ Excellent throughput!")
            elif throughput >= 100:
                responses.append("✅ Good throughput, meets target")
            elif throughput >= 50:
                responses.append("⚠️ Moderate throughput, room for improvement")
            else:
                responses.append("❌ Low throughput, scalability concerns")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_availability_analysis(context_data: List[Dict]) -> str:
        """Generate availability analysis"""
        responses = ["🛡️ **Availability Analysis**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            metrics = data.get("metrics", {})
            summary = metrics.get("summary", {})
            
            success_rate = summary.get("success_rate", 0)
            error_rate = metrics.get("error_rate", 0) * 100
            
            responses.append(f"""
**📁 {filename}**

**Availability Metrics:**
• Success Rate: {success_rate:.2f}%
• Failure Rate: {error_rate:.2f}%
• Uptime: {success_rate:.2f}%

**Target:** 99% availability
**Status:** {'✅ Exceeds target' if success_rate >= 99.5 else '✅ Meets target' if success_rate >= 99 else '⚠️ Below target' if success_rate >= 95 else '❌ Critical'}
""")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_comparison(context_data: List[Dict]) -> str:
        """Generate comparison with targets"""
        responses = ["📊 **Performance vs Targets Comparison**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            metrics = data.get("metrics", {})
            summary = metrics.get("summary", {})
            targets = summary.get("targets", {})
            
            sample_time = metrics.get("sample_time", {})
            avg_time = sample_time.get("mean", 0) / 1000
            p95 = sample_time.get("p95", 0) / 1000
            error_rate = metrics.get("error_rate", 0) * 100
            throughput = metrics.get("throughput", 0)
            success_rate = summary.get("success_rate", 0)
            sla_compliance = summary.get("sla_compliance_2s", 0)
            
            responses.append(f"""
**📁 {filename}**

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Availability | {success_rate:.1f}% | {targets.get('availability', 99)}% | {'✅' if success_rate >= targets.get('availability', 99) else '❌'} |
| Avg Response | {avg_time:.2f}s | <{targets.get('response_time', 2000)/1000:.0f}s | {'✅' if avg_time < targets.get('response_time', 2000)/1000 else '❌'} |
| Error Rate | {error_rate:.2f}% | <{targets.get('error_rate', 1)}% | {'✅' if error_rate < targets.get('error_rate', 1) else '❌'} |
| Throughput | {throughput:.0f}/s | {targets.get('throughput', 100)}/s | {'✅' if throughput >= targets.get('throughput', 100) else '❌'} |
| 95th Percentile | {p95:.2f}s | <{targets.get('p95_percentile', 3000)/1000:.0f}s | {'✅' if p95 < targets.get('p95_percentile', 3000)/1000 else '❌'} |
| SLA Compliance | {sla_compliance:.1f}% | >{targets.get('sla_compliance', 95)}% | {'✅' if sla_compliance >= targets.get('sla_compliance', 95) else '❌'} |
""")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_business_impact(context_data: List[Dict]) -> str:
        """Generate business impact analysis"""
        responses = ["💰 **Business Impact Assessment**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            metrics = data.get("metrics", {})
            summary = metrics.get("summary", {})
            
            error_rate = metrics.get("error_rate", 0) * 100
            sample_time = metrics.get("sample_time", {})
            avg_time = sample_time.get("mean", 0) / 1000
            
            responses.append(f"""
**📁 {filename}**

**Performance Impact:**
• Response Time Impact: {'High' if avg_time > 5 else 'Medium' if avg_time > 2 else 'Low'}
• Error Impact: {'High' if error_rate > 5 else 'Medium' if error_rate > 1 else 'Low'}

**Cost of Current Performance:**
• Error Rate ({error_rate:.2f}%): {'Major' if error_rate > 5 else 'Moderate'} revenue loss potential
• Response Time ({avg_time:.1f}s): {'Significant' if avg_time > 5 else 'Moderate'} productivity impact
• User Experience: {'Poor' if avg_time > 5 or error_rate > 5 else 'Acceptable'}

**Recommended Investment:**
• Timeline: 6 months for A+ grade
• Expected ROI: High (first year)
• Payback Period: 2-4 months
""")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_endpoint_analysis(context_data: List[Dict]) -> str:
        """Generate endpoint performance analysis"""
        responses = ["🔗 **Endpoint Performance Analysis**\n"]
        
        for data in context_data:
            filename = data.get("filename", "Unknown")
            metrics = data.get("metrics", {})
            summary = metrics.get("summary", {})
            
            transaction_stats = summary.get("transaction_stats", {})
            request_stats = summary.get("request_stats", {})
            
            responses.append(f"**📁 {filename}**\n")
            
            if transaction_stats:
                responses.append("\n**🔝 Top 5 Slowest Transactions:**")
                sorted_trans = sorted(transaction_stats.items(), 
                                     key=lambda x: x[1].get('avg_response', 0) or 0, 
                                     reverse=True)[:5]
                for label, data in sorted_trans:
                    avg = data.get('avg_response', 0) / 1000
                    err = data.get('error_rate', 0)
                    responses.append(f"• {label}: {avg:.2f}s (Error: {err:.2f}%)")
            
            if request_stats:
                responses.append("\n**🔝 Top 5 Slowest Requests:**")
                sorted_req = sorted(request_stats.items(), 
                                   key=lambda x: x[1].get('avg_response', 0) or 0, 
                                   reverse=True)[:5]
                for label, data in sorted_req:
                    avg = data.get('avg_response', 0) / 1000
                    err = data.get('error_rate', 0)
                    responses.append(f"• {label}: {avg:.2f}s (Error: {err:.2f}%)")
        
        return "\n".join(responses)
    
    @staticmethod
    def _generate_specific_metrics(context_data: List[Dict], message: str) -> str:
        """Generate response for specific metric queries"""
        message_lower = message.lower()
        
        if "70" in message_lower or "80" in message_lower or "90" in message_lower:
            return PerformanceChatbot._generate_response_time_analysis(context_data)
        elif "median" in message_lower:
            responses = ["📊 **Median Response Time**\n"]
            for data in context_data:
                filename = data.get("filename", "Unknown")
                metrics = data.get("metrics", {})
                sample_time = metrics.get("sample_time", {})
                median = sample_time.get("median", 0) / 1000
                responses.append(f"**{filename}**: {median:.2f}s")
            return "\n".join(responses)
        else:
            return PerformanceChatbot._generate_general_response(context_data, message)
    
    @staticmethod
    def _generate_general_response(context_data: List[Dict], message: str) -> str:
        """Generate general response"""
        return f"""🤖 I analyzed your query: "{message}"

Here's what I found:

""" + PerformanceChatbot._generate_overview_response(context_data) + """

**Need more specific information?** Try asking:
• "What are the critical issues?"
• "Show me response time percentiles"
• "What are your recommendations?"
• "Compare current vs target metrics"
• "Show me the slowest endpoints"
"""












