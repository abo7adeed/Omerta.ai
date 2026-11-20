# Omerta.ai — Sanctions & Watchlist Screening Agent
## Entity Resolution & Matching Methodology

**Document Version:** 1.0.0  
**Status:** Validated  
**Classification:** Algorithmic & Compliance Specification  

---

## 1. Algorithmic Overview

In AML sanctions compliance, matching accuracy requires balancing **high recall** (never missing a genuinely sanctioned target) against **precision** (preventing compliance analyst alert fatigue). 

The Omerta.ai matching engine employs a **multi-signal, explainable, and dynamically re-normalized scoring framework**. Instead of treating names as isolated strings, the engine fuses orthographic, phonetic, temporal, geographic, and identifier evidence into a deterministic confidence score:

$$\text{Confidence} = \max\left(0, \min\left(1, \sum_{i \in \text{Available}} \tilde{w}_i \cdot S_i + \sum_{j \in \text{Conflicts}} P_j\right)\right)$$

Where:
- $\tilde{w}_i$ is the dynamically re-normalized weight of attribute $i$
- $S_i$ is the positive corroboration score for attribute $i$
- $P_j$ is the penalty for explicit conflicting attribute $j$

---

## 2. Text Normalization Pipeline

### 2.1 Arabic Script Normalization
Arabic names exhibit high orthographic variance due to optional vowel marks (Tashkeel), morphological prefixes, and regional spellings:

1. **Tashkeel Stripping**: Removes diacritics including Fatha (`\u064E`), Damma (`\u064F`), Kasra (`\u0650`), Sukun (`\u0652`), Shadda (`\u0651`), Tanween (`\u064B-\u064D`), and Tatweel (`\u0640`).
2. **Hamza Unification**: Unifies `أ` (Alif with Hamza above), `إ` (Alif with Hamza below), `آ` (Alif with Madda), and `ٱ` (Wasla) into bare Alif `ا`.
3. **Orthographic Standardization**:
   - Taa Marbuta `ة` is mapped to Haa `ه`
   - Alif Maqsura `ى` is mapped to Yaa `ي`
4. **Prefix & Article Detachment**:
   - Leading definite article `ال` (*Al-* / *El-*) is stripped when preceding stems of length $>3$. For example, `السيد` $\rightarrow$ `سيد`.

### 2.2 Latin Script & Transliteration Normalization
1. **Case & Whitespace**: Standardizes to lowercase and collapses duplicate spaces.
2. **Honorific & Title Stripping**: Removes non-identifying titles (`Mr`, `Mrs`, `Ms`, `Dr`, `Eng`, `Sheikh`, `General`, `Sir`).
3. **Prefix Normalization**: Hyphenated prefixes like `al-`, `el-`, `abdel-`, `abdul-` are standardized to separated tokens (`al `, `el `, `abdel `).
4. **Phonetic Transliteration Mapping**: Maps common dialectal variations to canonical phonetic roots:
   - `muhammad`, `mohammed`, `mohammad`, `mahmoud` $\rightarrow$ `mohamed`
   - `ahmad` $\rightarrow$ `ahmed`
   - `usama` $\rightarrow$ `osama`
   - `tareq`, `tarek` $\rightarrow$ `tariq`
   - `abdul`, `abd` $\rightarrow$ `abdel`
   - `sayyed`, `alsayed`, `elsayed` $\rightarrow$ `sayed`

---

## 3. String Distance Formulations

The engine computes the composite name similarity $S_{\text{name}}$ using the maximum of three complementary metrics:

$$S_{\text{name}} = \max\left(S_{\text{JW}}, S_{\text{TokenSort}}, S_{\text{Substring}}\right)$$

### 3.1 Jaro-Winkler Similarity ($S_{\text{JW}}$)
Accounts for character transpositions and awards bonus weight to matching prefixes (up to 4 characters):

$$S_{\text{Jaro}} = \frac{1}{3}\left(\frac{m}{|s_1|} + \frac{m}{|s_2|} + \frac{m - t}{m}\right)$$
$$S_{\text{JW}} = S_{\text{Jaro}} + (\ell \cdot p \cdot (1 - S_{\text{Jaro}}))$$

Where $m$ is matching characters within distance $\left\lfloor\frac{\max(|s_1|, |s_2|)}{2}\right\rfloor - 1$, $t$ is half the number of transpositions, $\ell$ is prefix length ($\le 4$), and $p = 0.1$.

### 3.2 Token Sort Ratio ($S_{\text{TokenSort}}$)
Addresses word order permutations (e.g. *Bout, Viktor* vs *Viktor Bout*). Tokens are sorted alphabetically and evaluated via character sequence alignment:

$$S_{\text{TokenSort}} = \frac{2M}{|T_1| + |T_2|}$$

### 3.3 Substring Containment Bonus ($S_{\text{Substring}}$)
When one normalized name is completely contained within another and the length ratio exceeds $0.60$:

$$S_{\text{Substring}} = 0.90 + \left(0.10 \cdot \frac{\min(|s_1|, |s_2|)}{\max(|s_1|, |s_2|)}\right)$$

---

## 4. Multi-Signal Fusion & Dynamic Weight Re-Normalization

### 4.1 Base Weight Allocation

| Signal | Base Weight ($w_i$) | Corroboration Condition | Conflict Penalty ($P_j$) |
|:---|:---:|:---|:---:|
| **Name** | 0.50 | Max similarity across primary name & aliases | Drops if $S_{\text{name}} < 0.60$ |
| **Date of Birth** | 0.25 | Exact date = 1.0; Same year = 0.6 | **-0.35** if years differ by $>2$ years |
| **Country** | 0.15 | ISO-3166 match = 1.0 | **-0.20** if explicit different jurisdiction |
| **National / Tax ID** | 0.10 | Exact identifier match = 1.0 | **-0.30** if IDs conflict |

### 4.2 Dynamic Weight Re-Normalization
When optional secondary identifiers are absent from the query or target record (e.g., screening an organization without DOB, or an individual without tax ID), static weights artificially penalize the score.

The engine dynamically scales the positive corroboration weights across the set of active attributes $A$:

$$W_{\text{active}} = \sum_{k \in A} w_k$$
$$\tilde{w}_i = \frac{w_i}{W_{\text{active}}}$$

**Example:**
Screening a company with Name ($w=0.50$) and Country ($w=0.15$), where DOB and National ID are not applicable:
- $W_{\text{active}} = 0.50 + 0.15 = 0.65$
- $\tilde{w}_{\text{name}} = 0.50 / 0.65 \approx 0.769$
- $\tilde{w}_{\text{country}} = 0.15 / 0.65 \approx 0.231$
- If Name similarity is 1.0 and Country matches (1.0):
  $$\text{Confidence} = (0.769 \cdot 1.0) + (0.231 \cdot 1.0) = 1.00\ (100\%)$$

---

## 5. False Positive Suppression

1. **Date of Birth Disambiguation**:
   Common names (e.g. *Mohamed Ahmed*) are frequently shared. If the query specifies DOB `2002-11-30` and the sanctioned target was born in `1982-05-14`, the engine applies a **$-0.35$ penalty**, dropping the composite score below the screening threshold ($0.70$).
2. **Jurisdictional Conflict Penalty**:
   If an entity is known to operate strictly in Japan (`JP`) and the watchlist target is restricted to Egypt (`EG`), a **$-0.20$ penalty** suppresses false positives while keeping the candidate visible for secondary review if other identifiers align.
3. **Threshold Calibration**:
   - $\ge 0.85$: `POTENTIAL_MATCH` (Immediate compliance review; Red badge)
   - $0.65 - 0.84$: `NEEDS_HUMAN_REVIEW` (Secondary clearance queue; Amber badge)
   - $< 0.65$: `NO_MATCH` (Logged negative; Green badge)

