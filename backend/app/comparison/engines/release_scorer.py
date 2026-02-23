"""
Release Readiness Scorer
Calculates overall release health score and provides release verdict
"""

from typing import Dict, Any, Tuple, List


class ReleaseScorer:
    """
    Calculates release readiness score based on:
    - Backend Performance (40%)
    - Frontend UX (40%)
    - Reliability/Error Rate (20%)
    """
    
    # Score classification thresholds
    THRESHOLDS = {
        'excellent': 90.0,      # 90-100: Release Approved
        'acceptable': 75.0,     # 75-89: Monitor
        'risky': 60.0,          # 60-74: Approval Needed
        'blocked': 0.0          # <60: Release Blocked
    }
    
    # Weights for score components
    WEIGHTS = {
        'backend': 0.40,       # 40%
        'frontend': 0.40,      # 40%
        'reliability': 0.20    # 20%
    }
    
    def __init__(self):
        self.scores = {}
        self.verdict = None
        self.verdict_details = {}
    
    def calculate_release_score(
        self,
        jmeter_results: Dict[str, Any],
        lighthouse_results: Dict[str, Any],
        correlation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate overall release health score
        
        Args:
            jmeter_results: JMeter comparison results
            lighthouse_results: Lighthouse comparison results
            correlation_results: Correlation analysis results
        
        Returns:
            Complete release score and verdict
        """
        
        # Get component scores
        backend_score = jmeter_results.get('backend_score', 100.0)
        frontend_score = lighthouse_results.get('frontend_score', 100.0)
        reliability_score = self._calculate_reliability_score(jmeter_results)
        
        # Calculate weighted overall score
        overall_score = (
            backend_score * self.WEIGHTS['backend'] +
            frontend_score * self.WEIGHTS['frontend'] +
            reliability_score * self.WEIGHTS['reliability']
        )
        
        # Store scores
        self.scores = {
            'overall_score': round(overall_score, 2),
            'backend_score': round(backend_score, 2),
            'frontend_score': round(frontend_score, 2),
            'reliability_score': round(reliability_score, 2)
        }
        
        # Determine verdict
        self.verdict, self.verdict_details = self._determine_verdict(
            overall_score,
            jmeter_results,
            lighthouse_results,
            correlation_results
        )
        
        return {
            'scores': self.scores,
            'verdict': self.verdict,
            'verdict_details': self.verdict_details,
            'classification': self._classify_score(overall_score)
        }
    
    def _calculate_reliability_score(self, jmeter_results: Dict) -> float:
        """
        Calculate reliability score based on error rates
        
        Returns:
            Score from 0-100 (higher is better)
        """
        
        # Get error metrics from JMeter results
        error_regressions = [
            r for r in jmeter_results.get('regressions', [])
            if 'error rate' in r['metric_name'].lower() or 'error' in r['metric_name'].lower()
        ]
        
        new_failures = jmeter_results.get('new_failures', [])
        
        # Start with perfect score
        score = 100.0
        
        # Deduct for error rate regressions
        for regression in error_regressions:
            severity = regression.get('severity', 'minor')
            if severity == 'critical':
                score -= 25
            elif severity == 'major':
                score -= 15
            elif severity == 'minor':
                score -= 5
        
        # Deduct for new failures
        score -= len(new_failures) * 20
        
        # Clamp to 0-100
        return max(0.0, min(100.0, score))
    
    def _determine_verdict(
        self,
        overall_score: float,
        jmeter_results: Dict,
        lighthouse_results: Dict,
        correlation_results: Dict
    ) -> Tuple[str, Dict]:
        """
        Determine release verdict based on scores and analysis
        
        Returns:
            (verdict, details) where verdict is 'approved', 'monitor', 'approval_needed', or 'blocked'
        """
        
        classification = self._classify_score(overall_score)
        
        # Count critical issues
        jmeter_critical = len([r for r in jmeter_results.get('regressions', []) 
                              if r['severity'] == 'critical'])
        lighthouse_critical = len([r for r in lighthouse_results.get('regressions', []) 
                                   if r['severity'] == 'critical'])
        new_failures = len(jmeter_results.get('new_failures', []))
        ux_issues = len(lighthouse_results.get('ux_issues', []))
        
        # Blocking conditions (override score-based classification)
        blocking_reasons = []
        
        if new_failures > 0:
            blocking_reasons.append(f"{new_failures} new transaction failures detected")
        
        if jmeter_critical >= 3:
            blocking_reasons.append(f"{jmeter_critical} critical backend regressions")
        
        if lighthouse_critical >= 3:
            blocking_reasons.append(f"{lighthouse_critical} critical UX regressions")
        
        if self.scores['reliability_score'] < 40:
            blocking_reasons.append("Reliability score below acceptable threshold")
        
        # Determine final verdict
        if blocking_reasons:
            verdict = 'blocked'
            verdict_text = 'Release Blocked'
            recommendation = (
                "❌ **Do not proceed with release.** "
                "Critical issues must be resolved before deployment."
            )
        elif classification == 'excellent':
            verdict = 'approved'
            verdict_text = 'Release Approved'
            recommendation = (
                "✅ **Release approved.** "
                "All performance metrics are within acceptable ranges."
            )
        elif classification == 'acceptable':
            verdict = 'monitor'
            verdict_text = 'Release Acceptable (Monitor)'
            recommendation = (
                "⚠️ **Release can proceed with caution.** "
                "Monitor the deployment closely and be prepared to rollback if issues arise."
            )
        elif classification == 'risky':
            verdict = 'approval_needed'
            verdict_text = 'Release Risky (Approval Required)'
            recommendation = (
                "⚠️ **Management approval required.** "
                "Significant performance degradation detected. "
                "Risk must be accepted by stakeholders."
            )
        else:
            verdict = 'blocked'
            verdict_text = 'Release Blocked'
            recommendation = (
                "❌ **Release blocked due to poor performance score.** "
                "Address performance issues before proceeding."
            )
        
        # Build details
        details = {
            'verdict': verdict,
            'verdict_text': verdict_text,
            'recommendation': recommendation,
            'classification': classification,
            'blocking_reasons': blocking_reasons,
            'risk_factors': self._identify_risk_factors(
                jmeter_results, lighthouse_results, correlation_results
            ),
            'confidence': self._calculate_verdict_confidence(
                overall_score, jmeter_critical, lighthouse_critical
            )
        }
        
        return verdict, details
    
    def _classify_score(self, score: float) -> str:
        """Classify score into performance category"""
        
        if score >= self.THRESHOLDS['excellent']:
            return 'excellent'
        elif score >= self.THRESHOLDS['acceptable']:
            return 'acceptable'
        elif score >= self.THRESHOLDS['risky']:
            return 'risky'
        else:
            return 'blocked'
    
    def _identify_risk_factors(
        self,
        jmeter_results: Dict,
        lighthouse_results: Dict,
        correlation_results: Dict
    ) -> List[Dict]:
        """Identify specific risk factors for this release"""
        
        risk_factors = []
        
        # Backend risks
        jmeter_major_plus = len([r for r in jmeter_results.get('regressions', []) 
                                 if r['severity'] in ['critical', 'major']])
        if jmeter_major_plus > 0:
            risk_factors.append({
                'category': 'backend',
                'severity': 'high' if jmeter_major_plus >= 5 else 'medium',
                'description': f'{jmeter_major_plus} significant backend performance regressions',
                'impact': 'User-facing API response times may be slower'
            })
        
        # Frontend risks
        lighthouse_major_plus = len([r for r in lighthouse_results.get('regressions', []) 
                                     if r['severity'] in ['critical', 'major']])
        if lighthouse_major_plus > 0:
            risk_factors.append({
                'category': 'frontend',
                'severity': 'high' if lighthouse_major_plus >= 5 else 'medium',
                'description': f'{lighthouse_major_plus} significant UX degradations',
                'impact': 'Users may experience slower page loads and poor interactivity'
            })
        
        # UX-specific risks
        ux_issues = lighthouse_results.get('ux_issues', [])
        if ux_issues:
            critical_ux = sum(
                len([i for i in page['issues'] if i['severity'] == 'critical'])
                for page in ux_issues
            )
            if critical_ux > 0:
                risk_factors.append({
                    'category': 'ux',
                    'severity': 'high',
                    'description': f'{critical_ux} critical UX issues detected',
                    'impact': 'User experience may be significantly degraded'
                })
        
        # Error/reliability risks
        new_failures = jmeter_results.get('new_failures', [])
        if new_failures:
            risk_factors.append({
                'category': 'reliability',
                'severity': 'critical',
                'description': f'{len(new_failures)} new transaction failures',
                'impact': 'Features may be broken or unavailable to users'
            })
        
        # Correlation-based risks
        root_causes = correlation_results.get('root_causes', [])
        high_confidence_causes = [rc for rc in root_causes if rc['confidence'] == 'high']
        if high_confidence_causes:
            risk_factors.append({
                'category': 'systemic',
                'severity': 'high',
                'description': 'Correlated performance issues detected',
                'impact': 'Performance problems may indicate deeper systemic issues',
                'root_cause': high_confidence_causes[0]['type']
            })
        
        return risk_factors
    
    def _calculate_verdict_confidence(
        self,
        overall_score: float,
        jmeter_critical: int,
        lighthouse_critical: int
    ) -> str:
        """
        Calculate confidence level in the verdict
        
        Returns:
            'high', 'medium', or 'low'
        """
        
        # High confidence if score is very clear-cut
        if overall_score >= 95 or overall_score < 50:
            return 'high'
        
        # High confidence if there are many critical issues
        if jmeter_critical + lighthouse_critical >= 5:
            return 'high'
        
        # Medium confidence for middle-ground scores
        if 60 <= overall_score <= 90:
            return 'medium'
        
        return 'medium'
    
    def generate_executive_summary(
        self,
        jmeter_results: Dict,
        lighthouse_results: Dict,
        correlation_results: Dict
    ) -> str:
        """
        Generate natural language executive summary
        """
        
        lines = [
            "# Release Health Assessment\n",
            f"## Overall Release Score: **{self.scores['overall_score']}/100** "
            f"({self._classify_score(self.scores['overall_score']).upper()})\n",
            f"### Verdict: **{self.verdict_details['verdict_text']}**\n",
            f"{self.verdict_details['recommendation']}\n",
            "---\n",
            "## Component Scores:\n",
            f"- **Backend Performance**: {self.scores['backend_score']}/100",
            f"- **Frontend UX**: {self.scores['frontend_score']}/100",
            f"- **Reliability**: {self.scores['reliability_score']}/100\n",
        ]
        
        # Add risk factors
        if self.verdict_details['risk_factors']:
            lines.append("## Key Risk Factors:\n")
            for risk in self.verdict_details['risk_factors'][:5]:
                lines.append(
                    f"- **[{risk['severity'].upper()}]** {risk['description']}"
                )
                lines.append(f"  Impact: {risk['impact']}\n")
        
        # Add blocking reasons if any
        if self.verdict_details['blocking_reasons']:
            lines.append("\n## Blocking Issues:\n")
            for reason in self.verdict_details['blocking_reasons']:
                lines.append(f"- ❌ {reason}")
        
        # Add correlation insights
        root_causes = correlation_results.get('root_causes', [])
        if root_causes:
            primary = root_causes[0]
            lines.append(f"\n## Root Cause Analysis:\n")
            lines.append(f"**{primary['type'].replace('_', ' ').title()}** "
                        f"(Confidence: {primary['confidence'].upper()})")
            lines.append(f"\n{primary['description']}\n")
            lines.append(f"**Recommendation:** {primary['recommendation']}")
        
        return '\n'.join(lines)
