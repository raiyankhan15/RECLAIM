# ContextIQ: Methodology and Algorithm Specifications

This document formally describes the algorithms, data structures, and mathematical procedures implemented in the ContextIQ platform.

---

## Algorithm 1: Automated Browser Context-Switch & Interruption Episode Detection

Executed continuously inside the Chrome Extension background service worker (`background.js`):

```
Algorithm 1: TabSwitchAndInterruptionDetection
Input: activeTabId, previousTabId, primaryTabId, sessionId
State: isInterrupted (boolean), interruptionStartTime (timestamp), visitedDomains (list), episodeSwitches (integer)

1. When chrome.tabs.onActivated(activeInfo) fires:
2.   tab = chrome.tabs.get(activeInfo.tabId)
3.   currentTime = now()
4.   dwellDuration = currentTime - lastSwitchTimestamp
5.   sanitizedDomain, category = sanitizeUrl(tab.url)
6.   
7.   If activeInfo.tabId != primaryTabId AND isInterrupted == False then
8.       // User has departed the primary working task
9.       isInterrupted = True
10.      interruptionStartTime = currentTime
11.      currentEpisodeId = generateUuid()
12.      episodeSwitches = 1
13.      visitedDomains = [sanitizedDomain]
14.      dispatchApiPost("/events/tab-switch", {is_primary: False, is_interruption: True, ...})
15.
16.  Else if activeInfo.tabId != primaryTabId AND isInterrupted == True then
17.      // Multi-tab browsing during ongoing interruption
18.      episodeSwitches = episodeSwitches + 1
19.      if sanitizedDomain not in visitedDomains:
20.          visitedDomains.append(sanitizedDomain)
21.      dispatchApiPost("/events/tab-switch", {is_primary: False, is_interruption: True, ...})
22.
23.  Else if activeInfo.tabId == primaryTabId AND isInterrupted == True then
24.      // User has returned to the designated primary task
25.      totalEpisodeDuration = currentTime - interruptionStartTime
26.      dispatchApiPost("/events/tab-switch", {is_primary: True, is_interruption: False, ...})
27.      dispatchApiPost("/events/interruption-episode", {
28.          episode_id: currentEpisodeId,
29.          duration_sec: totalEpisodeDuration,
30.          switch_count: episodeSwitches,
31.          visited_domains: visitedDomains,
32.          recovery_status: "UNMEASURED_BROWSER"
33.      })
34.      isInterrupted = False
35.      interruptionStartTime = null
36.      episodeSwitches = 0
37.
38.  lastSwitchTimestamp = currentTime
```

---

## Algorithm 2: Three-Stage Controlled Recovery Measurement

Executed during controlled experimental trials (`core/experiment.py`):

```
Algorithm 2: ThreeStageRecoveryMeasurement
Input: Participant ID, Selected Condition (A, B, C, or D), Question Pools

Stage A: Baseline Establishment
1. Present disjoint Question Set Q_base (n questions of calibrated complexity)
2. Start Timer T_base_start
3. Upon participant submission:
4.   T_baseline = now() - T_base_start
5.   Acc_baseline = correct_answers / total_questions
6.   Err_baseline = incorrect_answers

Stage B: Interruption Challenge
7. If Condition == CONTROL then:
8.   T_interrupt = 0.0, switches = 0
9. Else:
10.  Present unannounced Memory Stimulus Sequence (tokens displayed for t_study)
11.  Start Timer T_interrupt_start
12.  Present cognitive distractor arithmetic checks and recall query
13.  Upon participant submission:
14.    T_interrupt = now() - T_interrupt_start
15.    switches = (Condition == REPEATED_SWITCH) ? 4 : 2

Stage C: Resumed Task Recovery
16. Present equivalent but distinct Question Set Q_recover (no shared questions with Q_base)
17. Start Timer T_rec_start
18. Upon participant submission:
19.   T_recovery = now() - T_rec_start
20.   Acc_recovery = correct_answers / total_questions
21.   Compute Context Recovery Cost:
22.     CRC_excess = max(0, T_recovery - T_baseline)
23.     CRC_ratio = T_recovery / max(0.1, T_baseline)
24.     Acc_diff = Acc_recovery - Acc_baseline
```

---

## Algorithm 3: Sustained Baseline Recovery Criteria

Validates whether post-interruption observations reach sustained baseline thresholds (`core/recovery.py`):

```
Algorithm 3: EvaluateSustainedRecovery
Input: T_baseline, Acc_baseline, recoveryObservations[], consecutiveThreshold (default: 2)

1. durThreshold = T_baseline * 1.15
2. accThreshold = Acc_baseline * 0.90
3. consecutiveStreak = 0
4. recoveryIndex = null

5. For each observation i in recoveryObservations:
6.   if (obs[i].duration <= durThreshold) AND (obs[i].accuracy >= accThreshold) then:
7.       consecutiveStreak = consecutiveStreak + 1
8.       if consecutiveStreak >= consecutiveThreshold AND recoveryIndex == null then:
9.           recoveryIndex = i
10.  else:
11.      consecutiveStreak = 0  // Streak broken

12. If recoveryIndex != null then:
13.    return {status: "RECOVERED", recoveryIdx: recoveryIndex, isSustained: True}
14. Else:
15.    return {status: "INCOMPLETE_RECOVERY", observationLimit: sum(obs.duration), isSustained: False}
```

---

## Algorithm 4: Leakage-Free Supervised Regression Pipeline

Guarantees strict separation between pre-recovery features and outcome variables (`ml/train.py`, `data/preprocessing.py`):

```
Algorithm 4: LeakageFreeModelTraining
Input: Dataset D from SQLite

1. Clean dataset: drop duplicate session_id, filter invalid durations (< 0)
2. Assert that no post-recovery variables exist in Feature Set X:
3.   Forbidden = {recovery_duration, recovery_accuracy, crc_ratio, accuracy_diff}
4.   Assert (FeatureSet ∩ Forbidden) == ∅
5. Extract Features X:
6.   X = [complexity_level, baseline_duration, baseline_accuracy, 
          interruption_duration, interruption_accuracy, switch_count, switch_density]
7. Extract Target y:
8.   y = crc_seconds
9. Grouped Train/Test Split:
10.  If unique(D.participant_id) >= 6:
11.      X_train, X_test, y_train, y_test = GroupShuffleSplit(groups=D.participant_id, test_size=0.2)
12.  Else:
13.      X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
14. Fit Models:
15.  M1 = Pipeline([StandardScaler(), LinearRegression()])
16.  M2 = RandomForestRegressor(n_estimators=120, max_depth=6)
17.  M3 = GradientBoostingRegressor(n_estimators=120, learning_rate=0.08)
18. For each M in [M1, M2, M3]:
19.    y_pred = M.predict(X_test)
20.    Compute MAE, RMSE, R²
21. Select optimal model based on minimum test RMSE
22. Persist models to disk using joblib.dump()
```

