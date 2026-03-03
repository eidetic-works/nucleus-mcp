# Nucleus Launch Readiness Checklist

**Target Launch:** Week of February 3, 2026 (Tuesday 10am PT)  
**Status:** IN PREPARATION

---

## Pre-Launch Checklist

### 1. Product Readiness

#### Core Tools (5 Launch Tools)
- [x] `brain_governance_status` - Verified working
- [x] `brain_write_engram` - Verified working
- [x] `brain_query_engrams` - Verified working
- [x] `brain_audit_log` - Verified working
- [ ] `brain_mount_server` - Needs async verification

#### Testing
- [x] Unit tests passing (64 tests)
- [x] DSoR tests passing (16/16)
- [x] Verification script created (`scripts/verify_launch_tools.py`)
- [x] Demo script working (`scripts/demo_60_seconds.py`)
- [ ] Manual testing in Claude Desktop
- [ ] Manual testing in Windsurf
- [ ] Manual testing in Cursor (optional)

#### Documentation
- [x] README with Quick Start
- [x] CHANGELOG updated (v0.6.0)
- [x] ROADMAP updated
- [x] Architecture docs (`docs/architecture/DSOR_V060.md`)
- [ ] API reference for 5 core tools
- [ ] Troubleshooting guide

### 2. Distribution

#### PyPI
- [ ] Version 0.6.0 ready
- [ ] Package description optimized
- [ ] Keywords set for discoverability
- [ ] Test installation works (`pip install mcp-server-nucleus`)

#### GitHub
- [ ] Repository public
- [ ] License file present (MIT)
- [ ] Contributing guidelines
- [ ] Issue templates
- [ ] README badges updated

### 3. Marketing Assets

#### Landing Page
- [ ] nucleussovereign.com live
- [ ] "Quick Start in 2 Minutes" section
- [ ] 60-second demo video embedded
- [ ] Pricing tiers displayed
- [ ] "Context vs Control" comparison table

#### Demo Video
- [x] Script created (`scripts/demo_60_seconds.py`)
- [ ] Video recorded (60 seconds)
- [ ] Uploaded to YouTube
- [ ] Thumbnail created
- [ ] Embedded on landing page

#### Social Media
- [ ] Twitter/X thread drafted
- [ ] HN post drafted
- [ ] Reddit post drafted (r/MachineLearning, r/LocalLLaMA)
- [ ] LinkedIn post drafted

### 4. Community

#### Discord
- [ ] Server created
- [ ] Channels: #general, #bugs, #showcase, #announcements
- [ ] Welcome message configured
- [ ] Invite link ready

#### Support
- [ ] Email setup (hello@nucleussovereign.com)
- [ ] GitHub Issues enabled
- [ ] FAQ started

### 5. Legal & Compliance

- [ ] Privacy Policy (Termly template)
- [ ] Terms of Service
- [ ] MIT License in repo
- [ ] Cookie consent (if landing page uses cookies)

### 6. Monitoring

- [ ] PyPI download tracking
- [ ] GitHub star tracking
- [ ] Error reporting (Sentry optional)
- [ ] Usage analytics (PostHog optional)

---

## Launch Day Checklist

### Pre-Launch (Day Before)
- [ ] Final test of `pip install mcp-server-nucleus`
- [ ] Landing page reviewed
- [ ] Demo video uploaded
- [ ] All posts drafted and reviewed
- [ ] Discord invite link tested

### Launch (Tuesday 10am PT)
1. [ ] Post to Hacker News
2. [ ] Post to Reddit (r/MachineLearning)
3. [ ] Post to Reddit (r/LocalLLaMA)
4. [ ] Tweet thread
5. [ ] LinkedIn post
6. [ ] Discord announcement

### Post-Launch (First 8 Hours)
- [ ] Monitor HN for comments (respond within 1 hour)
- [ ] Monitor Reddit for comments
- [ ] Monitor Twitter for mentions
- [ ] Fix any critical bugs immediately
- [ ] Update FAQ with common questions

---

## Post-Launch Plan (30 Days)

### Week 1: Stabilization
- [ ] Fix all reported bugs
- [ ] Respond to all feedback
- [ ] Collect user testimonials
- [ ] Monitor Active Mounts metric

### Week 2: Iteration
- [ ] Add top-requested feature
- [ ] Publish first blog post
- [ ] Create second demo video

### Week 3: Amplification
- [ ] Write case study from early user
- [ ] Reach out to AI influencers
- [ ] Submit to Product Hunt (if ready)

### Week 4: Pro Tier
- [ ] Launch Pro tier ($29/mo)
- [ ] Enable usage-based upsell
- [ ] Announce on all channels

---

## Success Metrics (30 Days)

| Metric | Target | Status |
|--------|--------|--------|
| PyPI Downloads | 500+ | ⬜ |
| Active Mounts (weekly) | 100+ | ⬜ |
| GitHub Stars | 200+ | ⬜ |
| Discord Members | 50+ | ⬜ |
| Pro Tier Signups | 10+ | ⬜ |

**Success Criteria:** 2/3 of first three metrics = SUCCESS

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Critical bug at launch | Have rollback ready, respond within 1 hour |
| Negative feedback | Respond graciously, fix fast |
| Low traction | Adjust messaging, try different channels |
| MCP confusion | Add "What is MCP?" explainer |
| Competition announcement | Focus on governance differentiator |

---

## Contacts

- **Founder:** [Your name]
- **Support Email:** hello@nucleussovereign.com
- **Discord:** [Invite link TBD]
- **GitHub:** https://github.com/[org]/nucleus

---

*Checklist created January 30, 2026*
