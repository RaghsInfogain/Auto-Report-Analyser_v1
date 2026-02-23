"""
Lighthouse/Web Vitals Comparison Engine
Compares frontend UX metrics between baseline and current runs
"""

from typing import Dict, List, Any


class LighthouseComparisonEngine:
    """
    Compares Lighthouse and Web Vitals metrics to detect UX regressions
    """
    
    # UX regression thresholds
    THRESHOLDS = {
        'lcp_increase': 20.0,        # LCP increase >20% = UX degraded
        'cls_critical': 0.25,         # CLS >0.25 = Layout instability
        'tbt_increase': 30.0,         # TBT increase >30% = Blocking issue
        'performance_score_drop': 10  # Score drop >10 points = Release risk
    }
    
    # Classification thresholds
    CHANGE_THRESHOLDS = {
        'stable': 5.0,
        'minor': 15.0,
        'major': 30.0,
        'critical': 30.0
    }
    
    def __init__(self):
        self.results = {
            'regressions': [],
            'improvements': [],
            'stable_metrics': [],
            'ux_issues': [],
            'frontend_score': 0.0,
            'summary': {}
        }
    
    def compare(self, baseline_metrics: Dict[str, Any], current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main comparison method for Lighthouse metrics
        
        Args:
            baseline_metrics: Lighthouse metrics from baseline
            current_metrics: Lighthouse metrics from current run
        
        Returns:
            Comprehensive UX comparison results
        """
        
        # Compare per-page metrics
        self._compare_page_metrics(baseline_metrics, current_metrics)
        
        # Detect UX issues
        self._detect_ux_issues(baseline_metrics, current_metrics)
        
        # Calculate frontend score
        self._calculate_frontend_score()
        
        return self.results
    
    def _compare_page_metrics(self, baseline: Dict, current: Dict):
        """Compare Lighthouse metrics for each page"""
        
        # Handle both single-page and multi-page lighthouse data
        baseline_pages = self._extract_pages(baseline)
        current_pages = self._extract_pages(current)
        
        all_pages = set(baseline_pages.keys()) | set(current_pages.keys())
        
        for page_url in all_pages:
            baseline_page = baseline_pages.get(page_url, {})
            current_page = current_pages.get(page_url, {})
            
            if not baseline_page:
                # New page
                self.results['summary'][f'new_page_{page_url}'] = {
                    'type': 'new_page',
                    'performance_score': current_page.get('performance_score')
                }
                continue
            
            if not current_page:
                # Removed page
                self.results['summary'][f'removed_page_{page_url}'] = {
                    'type': 'removed_page'
                }
                continue
            
            # Compare key metrics
            self._compare_lighthouse_metrics(page_url, baseline_page, current_page)
    
    def _compare_lighthouse_metrics(self, page_url: str, baseline: Dict, current: Dict):
        """Compare specific Lighthouse metrics for a page"""
        
        metrics_to_compare = [
            # (metric_key, display_name, unit, direction, critical_threshold)
            ('performance_score', 'Performance Score', 'points', 'higher_is_better', 
             self.THRESHOLDS['performance_score_drop']),
            ('lcp', 'Largest Contentful Paint (LCP)', 'ms', 'lower_is_better', 
             self.THRESHOLDS['lcp_increase']),
            ('cls', 'Cumulative Layout Shift (CLS)', 'score', 'lower_is_better', None),
            ('fcp', 'First Contentful Paint (FCP)', 'ms', 'lower_is_better', None),
            ('tbt', 'Total Blocking Time (TBT)', 'ms', 'lower_is_better', 
             self.THRESHOLDS['tbt_increase']),
            ('speed_index', 'Speed Index', 'ms', 'lower_is_better', None),
            ('tti', 'Time to Interactive (TTI)', 'ms', 'lower_is_better', None),
        ]
        
        for metric_key, metric_name, unit, direction, critical_threshold in metrics_to_compare:
            baseline_value = self._get_metric_value(baseline, metric_key)
            current_value = self._get_metric_value(current, metric_key)
            
            if baseline_value is not None and current_value is not None:
                comparison = self._compare_metric(
                    metric_name=f"{page_url} - {metric_name}",
                    baseline_value=baseline_value,
                    current_value=current_value,
                    unit=unit,
                    direction=direction,
                    page_url=page_url,
                    metric_key=metric_key,
                    critical_threshold=critical_threshold
                )
                
                self._categorize_comparison(comparison)
    
    def _compare_metric(
        self,
        metric_name: str,
        baseline_value: float,
        current_value: float,
        unit: str,
        direction: str,
        page_url: str,
        metric_key: str,
        critical_threshold: float = None
    ) -> Dict[str, Any]:
        """Compare a single Lighthouse metric"""
        
        # Calculate change
        if baseline_value == 0:
            change_percent = 100.0 if current_value > 0 else 0.0
        else:
            change_percent = ((current_value - baseline_value) / baseline_value) * 100
        
        change_absolute = current_value - baseline_value
        
        # Determine if this is regression or improvement
        if direction == 'lower_is_better':
            is_regression = change_percent > 0
        else:  # higher_is_better
            is_regression = change_percent < 0
        
        # Classify severity
        severity = self._classify_severity(
            change_percent=abs(change_percent),
            metric_key=metric_key,
            is_regression=is_regression,
            critical_threshold=critical_threshold,
            current_value=current_value
        )
        
        return {
            'metric_name': metric_name,
            'page_url': page_url,
            'baseline_value': baseline_value,
            'current_value': current_value,
            'change_percent': round(change_percent, 2),
            'change_absolute': round(change_absolute, 2),
            'unit': unit,
            'severity': severity,
            'is_regression': is_regression,
            'direction': direction,
            'metric_key': metric_key
        }
    
    def _classify_severity(
        self,
        change_percent: float,
        metric_key: str,
        is_regression: bool,
        critical_threshold: float = None,
        current_value: float = None
    ) -> str:
        """Classify severity of Lighthouse metric change"""
        
        if not is_regression:
            return 'improvement'
        
        # Check metric-specific critical thresholds
        if critical_threshold is not None:
            if change_percent > critical_threshold:
                return 'critical'
        
        # CLS absolute value check
        if metric_key == 'cls' and current_value is not None:
            if current_value > self.THRESHOLDS['cls_critical']:
                return 'critical'
        
        # Apply standard thresholds
        if change_percent < self.CHANGE_THRESHOLDS['stable']:
            return 'stable'
        elif change_percent < self.CHANGE_THRESHOLDS['minor']:
            return 'minor'
        elif change_percent < self.CHANGE_THRESHOLDS['major']:
            return 'major'
        else:
            return 'critical'
    
    def _categorize_comparison(self, comparison: Dict[str, Any]):
        """Categorize comparison into appropriate result bucket"""
        
        severity = comparison['severity']
        is_regression = comparison['is_regression']
        
        if severity == 'improvement' or not is_regression:
            self.results['improvements'].append(comparison)
        elif severity == 'stable':
            self.results['stable_metrics'].append(comparison)
        else:
            self.results['regressions'].append(comparison)
    
    def _detect_ux_issues(self, baseline: Dict, current: Dict):
        """Detect specific UX degradation patterns"""
        
        baseline_pages = self._extract_pages(baseline)
        current_pages = self._extract_pages(current)
        
        for page_url, current_page in current_pages.items():
            baseline_page = baseline_pages.get(page_url, {})
            
            if not baseline_page:
                continue
            
            issues = []
            
            # Check LCP degradation
            baseline_lcp = self._get_metric_value(baseline_page, 'lcp')
            current_lcp = self._get_metric_value(current_page, 'lcp')
            if baseline_lcp and current_lcp:
                lcp_increase_pct = ((current_lcp - baseline_lcp) / baseline_lcp) * 100
                if lcp_increase_pct > self.THRESHOLDS['lcp_increase']:
                    issues.append({
                        'type': 'lcp_degradation',
                        'description': f'LCP increased by {lcp_increase_pct:.1f}% - User experience degraded',
                        'baseline': baseline_lcp,
                        'current': current_lcp,
                        'severity': 'critical'
                    })
            
            # Check CLS issues
            current_cls = self._get_metric_value(current_page, 'cls')
            if current_cls and current_cls > self.THRESHOLDS['cls_critical']:
                issues.append({
                    'type': 'cls_instability',
                    'description': f'CLS of {current_cls:.3f} indicates layout instability',
                    'current': current_cls,
                    'severity': 'critical'
                })
            
            # Check TBT blocking
            baseline_tbt = self._get_metric_value(baseline_page, 'tbt')
            current_tbt = self._get_metric_value(current_page, 'tbt')
            if baseline_tbt and current_tbt:
                tbt_increase_pct = ((current_tbt - baseline_tbt) / baseline_tbt) * 100
                if tbt_increase_pct > self.THRESHOLDS['tbt_increase']:
                    issues.append({
                        'type': 'tbt_blocking',
                        'description': f'TBT increased by {tbt_increase_pct:.1f}% - Frontend blocking issue',
                        'baseline': baseline_tbt,
                        'current': current_tbt,
                        'severity': 'major'
                    })
            
            # Check performance score drop
            baseline_score = self._get_metric_value(baseline_page, 'performance_score')
            current_score = self._get_metric_value(current_page, 'performance_score')
            if baseline_score and current_score:
                score_drop = baseline_score - current_score
                if score_drop > self.THRESHOLDS['performance_score_drop']:
                    issues.append({
                        'type': 'performance_score_drop',
                        'description': f'Performance score dropped by {score_drop:.0f} points - Release risk',
                        'baseline': baseline_score,
                        'current': current_score,
                        'severity': 'critical'
                    })
            
            if issues:
                self.results['ux_issues'].append({
                    'page_url': page_url,
                    'issues': issues
                })
    
    def _calculate_frontend_score(self):
        """Calculate overall frontend UX score (0-100)"""
        
        # Count metrics by severity
        critical_count = len([r for r in self.results['regressions'] if r['severity'] == 'critical'])
        major_count = len([r for r in self.results['regressions'] if r['severity'] == 'major'])
        minor_count = len([r for r in self.results['regressions'] if r['severity'] == 'minor'])
        improvement_count = len(self.results['improvements'])
        stable_count = len(self.results['stable_metrics'])
        ux_issue_count = sum(len(page['issues']) for page in self.results['ux_issues'])
        
        total_comparisons = (critical_count + major_count + minor_count + 
                           improvement_count + stable_count)
        
        if total_comparisons == 0:
            self.results['frontend_score'] = 100.0
            return
        
        # Penalty scoring
        penalties = 0
        penalties += critical_count * 20
        penalties += major_count * 10
        penalties += minor_count * 5
        penalties += ux_issue_count * 15  # UX issues are serious
        
        # Bonus for improvements
        bonuses = improvement_count * 3
        
        # Start from 100 and apply penalties/bonuses
        score = 100 - penalties + bonuses
        
        # Clamp to 0-100
        self.results['frontend_score'] = max(0.0, min(100.0, score))
        
        # Store summary
        self.results['summary']['total_comparisons'] = total_comparisons
        self.results['summary']['critical_regressions'] = critical_count
        self.results['summary']['major_regressions'] = major_count
        self.results['summary']['minor_regressions'] = minor_count
        self.results['summary']['improvements'] = improvement_count
        self.results['summary']['stable_metrics'] = stable_count
        self.results['summary']['ux_issues'] = ux_issue_count
    
    def _extract_pages(self, metrics: Dict) -> Dict[str, Dict]:
        """
        Extract page-level metrics from Lighthouse data
        Handles both single-page and multi-page structures
        """
        
        pages = {}
        
        # Check if this is multi-page data
        if 'pages' in metrics and isinstance(metrics['pages'], dict):
            return metrics['pages']
        
        # Check if this is a list of pages
        if isinstance(metrics, list):
            for page_data in metrics:
                url = page_data.get('url', page_data.get('page_url', 'Unknown'))
                pages[url] = page_data
            return pages
        
        # Single page data - use URL as key or 'default'
        url = metrics.get('url', metrics.get('page_url', 'default_page'))
        pages[url] = metrics
        
        return pages
    
    def _get_metric_value(self, page_data: Dict, metric_key: str) -> float:
        """Extract metric value from page data, handling various structures"""
        
        # Direct key
        if metric_key in page_data:
            return page_data[metric_key]
        
        # Nested in 'metrics'
        if 'metrics' in page_data and isinstance(page_data['metrics'], dict):
            if metric_key in page_data['metrics']:
                return page_data['metrics'][metric_key]
        
        # Nested in 'audits' (Lighthouse JSON structure)
        if 'audits' in page_data and isinstance(page_data['audits'], dict):
            audit_key_map = {
                'lcp': 'largest-contentful-paint',
                'cls': 'cumulative-layout-shift',
                'fcp': 'first-contentful-paint',
                'tbt': 'total-blocking-time',
                'tti': 'interactive',
                'speed_index': 'speed-index'
            }
            
            lighthouse_key = audit_key_map.get(metric_key)
            if lighthouse_key and lighthouse_key in page_data['audits']:
                audit = page_data['audits'][lighthouse_key]
                if isinstance(audit, dict) and 'numericValue' in audit:
                    return audit['numericValue']
        
        # Performance score from categories
        if metric_key == 'performance_score' and 'categories' in page_data:
            if 'performance' in page_data['categories']:
                perf = page_data['categories']['performance']
                if isinstance(perf, dict) and 'score' in perf:
                    return perf['score'] * 100  # Convert 0-1 to 0-100
        
        return None
    
    def get_top_ux_issues(self, limit: int = 10) -> List[Dict]:
        """Get top UX issues across all pages"""
        
        all_issues = []
        for page_data in self.results['ux_issues']:
            for issue in page_data['issues']:
                all_issues.append({
                    'page_url': page_data['page_url'],
                    **issue
                })
        
        # Sort by severity (critical first)
        severity_order = {'critical': 0, 'major': 1, 'minor': 2}
        return sorted(all_issues, key=lambda x: severity_order.get(x['severity'], 3))[:limit]
    
    def get_worst_pages(self) -> List[Dict]:
        """Get pages with worst performance regressions"""
        
        page_scores = {}
        
        for regression in self.results['regressions']:
            page_url = regression['page_url']
            if page_url not in page_scores:
                page_scores[page_url] = {'url': page_url, 'regression_count': 0, 'total_change': 0}
            
            page_scores[page_url]['regression_count'] += 1
            page_scores[page_url]['total_change'] += abs(regression['change_percent'])
        
        # Sort by regression count and total change
        sorted_pages = sorted(
            page_scores.values(),
            key=lambda x: (x['regression_count'], x['total_change']),
            reverse=True
        )
        
        return sorted_pages[:10]
