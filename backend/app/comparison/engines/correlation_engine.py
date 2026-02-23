"""
Correlation Intelligence Engine
Correlates backend (JMeter) and frontend (Lighthouse) metrics
to identify root causes of performance issues
"""

from typing import Dict, List, Any, Optional


class CorrelationEngine:
    """
    Analyzes correlations between backend and frontend performance
    to provide intelligent root cause analysis
    """
    
    def __init__(self):
        self.insights = []
        self.root_causes = []
    
    def correlate(
        self,
        jmeter_results: Dict[str, Any],
        lighthouse_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Correlate JMeter and Lighthouse comparison results
        
        Args:
            jmeter_results: Results from JMeter comparison
            lighthouse_results: Results from Lighthouse comparison
        
        Returns:
            Correlation insights and root cause analysis
        """
        
        # Rule 1: Backend performance impact
        self._detect_backend_impact(jmeter_results, lighthouse_results)
        
        # Rule 2: Frontend rendering issues
        self._detect_frontend_issues(jmeter_results, lighthouse_results)
        
        # Rule 3: Scalability problems
        self._detect_scalability_issues(jmeter_results)
        
        # Rule 4: Error handling impact
        self._detect_error_handling_issues(jmeter_results, lighthouse_results)
        
        # Rule 5: Resource contention
        self._detect_resource_contention(jmeter_results, lighthouse_results)
        
        return {
            'insights': self.insights,
            'root_causes': self.root_causes,
            'correlation_score': self._calculate_correlation_score()
        }
    
    def _detect_backend_impact(self, jmeter: Dict, lighthouse: Dict):
        """
        Detect if backend performance is impacting frontend
        
        Rule: IF JMeter response time increased AND TTFB increased
              → Backend problem
        """
        
        # Check JMeter response time regressions
        jmeter_rt_regressions = [
            r for r in jmeter.get('regressions', [])
            if 'response time' in r['metric_name'].lower()
        ]
        
        # Check Lighthouse TTFB or server response time
        lighthouse_ttfb_regressions = [
            r for r in lighthouse.get('regressions', [])
            if any(key in r.get('metric_key', '').lower() 
                  for key in ['ttfb', 'server-response-time', 'fcp'])
        ]
        
        if jmeter_rt_regressions and lighthouse_ttfb_regressions:
            # Calculate average increases
            avg_jmeter_increase = sum(
                abs(r['change_percent']) for r in jmeter_rt_regressions
            ) / len(jmeter_rt_regressions)
            
            avg_lighthouse_increase = sum(
                abs(r['change_percent']) for r in lighthouse_ttfb_regressions
            ) / len(lighthouse_ttfb_regressions)
            
            self.root_causes.append({
                'type': 'backend_performance',
                'confidence': 'high',
                'description': (
                    f'Backend performance degradation detected: '
                    f'JMeter response times increased by {avg_jmeter_increase:.1f}% '
                    f'and frontend server response times increased by {avg_lighthouse_increase:.1f}%'
                ),
                'affected_metrics': {
                    'jmeter': [r['metric_name'] for r in jmeter_rt_regressions[:3]],
                    'lighthouse': [r['metric_name'] for r in lighthouse_ttfb_regressions[:3]]
                },
                'recommendation': (
                    'Investigate backend API performance, database queries, '
                    'and server resource utilization.'
                )
            })
            
            self.insights.append({
                'type': 'correlation_found',
                'message': 'Backend performance issues are impacting frontend load times'
            })
    
    def _detect_frontend_issues(self, jmeter: Dict, lighthouse: Dict):
        """
        Detect frontend-specific rendering issues
        
        Rule: IF JMeter stable BUT LCP and TBT increased
              → Frontend rendering issue
        """
        
        # Check if JMeter is mostly stable
        jmeter_critical = len([r for r in jmeter.get('regressions', []) 
                              if r['severity'] == 'critical'])
        jmeter_stable = len(jmeter.get('stable_metrics', []))
        
        # Check Lighthouse rendering metrics
        lighthouse_rendering_issues = [
            r for r in lighthouse.get('regressions', [])
            if any(key in r.get('metric_key', '').lower() 
                  for key in ['lcp', 'tbt', 'cls', 'tti'])
        ]
        
        if jmeter_critical == 0 and lighthouse_rendering_issues:
            avg_rendering_increase = sum(
                abs(r['change_percent']) for r in lighthouse_rendering_issues
            ) / len(lighthouse_rendering_issues)
            
            self.root_causes.append({
                'type': 'frontend_rendering',
                'confidence': 'high',
                'description': (
                    f'Frontend rendering issue detected: '
                    f'Backend APIs are stable but UX metrics degraded by {avg_rendering_increase:.1f}%'
                ),
                'affected_metrics': [r['metric_name'] for r in lighthouse_rendering_issues[:5]],
                'recommendation': (
                    'Review frontend JavaScript execution, render-blocking resources, '
                    'and client-side processing. Check for new third-party scripts or increased DOM complexity.'
                )
            })
            
            self.insights.append({
                'type': 'frontend_specific',
                'message': 'Frontend rendering performance degraded despite stable backend'
            })
    
    def _detect_scalability_issues(self, jmeter: Dict):
        """
        Detect scalability/resource issues
        
        Rule: IF throughput drops with same user load
              → Scalability issue
        """
        
        throughput_regressions = [
            r for r in jmeter.get('regressions', [])
            if 'throughput' in r['metric_name'].lower()
        ]
        
        if throughput_regressions:
            for regression in throughput_regressions:
                if abs(regression['change_percent']) > 15:  # >15% throughput drop
                    self.root_causes.append({
                        'type': 'scalability',
                        'confidence': 'medium',
                        'description': (
                            f'Scalability issue detected: '
                            f'Throughput decreased by {abs(regression["change_percent"]):.1f}% '
                            f'under similar load'
                        ),
                        'affected_metrics': [regression['metric_name']],
                        'recommendation': (
                            'Investigate server resource utilization (CPU, memory, I/O), '
                            'database connection pools, and application thread pools. '
                            'Consider horizontal scaling or resource optimization.'
                        )
                    })
                    
                    self.insights.append({
                        'type': 'capacity_concern',
                        'message': 'System may be approaching capacity limits'
                    })
    
    def _detect_error_handling_issues(self, jmeter: Dict, lighthouse: Dict):
        """
        Detect error handling impact
        
        Rule: IF error rate increases AND response times increase
              → Backend error handling issue
        """
        
        error_rate_regressions = [
            r for r in jmeter.get('regressions', [])
            if 'error rate' in r['metric_name'].lower()
        ]
        
        response_time_regressions = [
            r for r in jmeter.get('regressions', [])
            if 'response time' in r['metric_name'].lower()
        ]
        
        new_failures = jmeter.get('new_failures', [])
        
        if (error_rate_regressions or new_failures) and response_time_regressions:
            self.root_causes.append({
                'type': 'error_handling',
                'confidence': 'high',
                'description': (
                    f'Error handling issues detected: '
                    f'{len(error_rate_regressions)} error rate increases and '
                    f'{len(new_failures)} new failures, coupled with response time degradation'
                ),
                'affected_metrics': {
                    'errors': [r['metric_name'] for r in error_rate_regressions[:3]],
                    'new_failures': [f['transaction_name'] for f in new_failures[:3]],
                    'response_times': [r['metric_name'] for r in response_time_regressions[:3]]
                },
                'recommendation': (
                    'Review error handling logic, exception handling paths, '
                    'and retry mechanisms. Check application logs for error patterns.'
                )
            })
            
            self.insights.append({
                'type': 'reliability_concern',
                'message': 'Increased error rates are impacting overall performance'
            })
    
    def _detect_resource_contention(self, jmeter: Dict, lighthouse: Dict):
        """
        Detect resource contention issues
        
        Rule: IF multiple metrics degrade across backend and frontend
              → Possible resource contention
        """
        
        jmeter_critical = len([r for r in jmeter.get('regressions', []) 
                              if r['severity'] in ['critical', 'major']])
        
        lighthouse_critical = len([r for r in lighthouse.get('regressions', []) 
                                   if r['severity'] in ['critical', 'major']])
        
        # Widespread degradation across both
        if jmeter_critical >= 3 and lighthouse_critical >= 3:
            self.root_causes.append({
                'type': 'resource_contention',
                'confidence': 'medium',
                'description': (
                    f'Widespread performance degradation detected: '
                    f'{jmeter_critical} backend regressions and '
                    f'{lighthouse_critical} frontend regressions suggest resource contention'
                ),
                'affected_areas': ['backend', 'frontend'],
                'recommendation': (
                    'Investigate system-wide resource constraints: '
                    'server CPU/memory, network bandwidth, database connections, '
                    'disk I/O, and shared service dependencies.'
                )
            })
            
            self.insights.append({
                'type': 'systemic_issue',
                'message': 'System-wide performance degradation indicates infrastructure concerns'
            })
    
    def _calculate_correlation_score(self) -> float:
        """
        Calculate a correlation score indicating confidence in root cause analysis
        
        Returns:
            Score from 0-100, where higher means more confident correlations
        """
        
        if not self.root_causes:
            return 0.0
        
        # Weight by confidence
        confidence_weights = {'high': 30, 'medium': 20, 'low': 10}
        
        total_score = sum(
            confidence_weights.get(rc['confidence'], 10)
            for rc in self.root_causes
        )
        
        # Clamp to 0-100
        return min(100.0, total_score)
    
    def get_primary_root_cause(self) -> Optional[Dict]:
        """Get the most likely root cause"""
        
        if not self.root_causes:
            return None
        
        # Sort by confidence
        confidence_order = {'high': 0, 'medium': 1, 'low': 2}
        sorted_causes = sorted(
            self.root_causes,
            key=lambda x: confidence_order.get(x['confidence'], 3)
        )
        
        return sorted_causes[0]
    
    def generate_summary(self) -> str:
        """Generate a natural language summary of correlations"""
        
        if not self.root_causes:
            return "No significant correlations detected between backend and frontend metrics."
        
        primary = self.get_primary_root_cause()
        
        summary_lines = [
            f"**Root Cause Analysis Summary**\n",
            f"Primary Issue: **{primary['type'].replace('_', ' ').title()}** "
            f"(Confidence: {primary['confidence'].upper()})\n",
            f"{primary['description']}\n",
            f"\n**Recommendation:**",
            f"{primary['recommendation']}\n"
        ]
        
        if len(self.root_causes) > 1:
            summary_lines.append(f"\n**Additional Concerns:**")
            for cause in self.root_causes[1:]:
                summary_lines.append(
                    f"- {cause['type'].replace('_', ' ').title()}: {cause['description']}"
                )
        
        return '\n'.join(summary_lines)
