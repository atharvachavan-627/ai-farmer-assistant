/**
 * UI PREVIEW MODE - development only.
 *
 * Lets you click through the interface without a backend. It replaces the HTTP transport of the
 * shared axios client with an in-browser stub. Everything it returns is sample data, NOT real
 * model output. It is only loaded by `npm run dev:preview` (see main.jsx) and is never part of
 * a production build.
 */
import { AxiosError } from 'axios';
import { apiClient } from '../services/apiClient';

const SESSION_KEY = 'afa.preview.session';
const HISTORY_KEY = 'afa.preview.history';
const USERS_KEY = 'afa.preview.users';

const read = (key, fallback) => {
  try {
    const v = sessionStorage.getItem(key);
    return v ? JSON.parse(v) : fallback;
  } catch {
    return fallback;
  }
};
const write = (key, value) => {
  try {
    if (value == null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore */
  }
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- Sample disease content (generic; deliberately contains NO chemical products or doses) ----
const DISEASES = [
  {
    "disease_code": "Potato___Early_blight",
    "name": "Early Blight",
    "crop": "potato",
    "category": "Fungal",
    "created_at": "2026-09-25T09:00:00Z",
    "image_url": "/images/diseases/Potato___Early_blight.jpg",
    "symptoms_summary": "Dark brown lesions with characteristic concentric target-board rings on older leaves.",
    "prevention_summary": "Plant certified seed tubers, rotate crops for 2 to 3 years, and minimize leaf wetness.",
    "overview": "A foliar fungal disease caused by Alternaria solani that predominantly infects mature lower foliage, causing dark concentric spots, premature leaf drop, and tuber yield loss.",
    "symptoms": [
      "Dark brown to black circular lesions on older lower leaves.",
      "Characteristic concentric rings producing a target-board pattern.",
      "Yellow chlorotic halos surrounding necrotic spots."
    ],
    "favourable_conditions": [
      "Warm temperatures between 24\u00b0C and 29\u00b0C (75\u00b0F\u201385\u00b0F).",
      "Alternating cycles of wet weather (dew, rain) and warm dry intervals."
    ],
    "preventive_measures": [
      "Plant certified disease-free seed tubers.",
      "Select resistant or early-maturing potato cultivars.",
      "Practice a 2 to 3-year crop rotation with non-solanaceous crops (e.g., corn, grasses, legumes)."
    ],
    "cultural_management": [
      "Use drip or furrow irrigation to minimize leaf wetness duration.",
      "Avoid overhead watering, especially late in the afternoon."
    ],
    "organic_management": [
      "Fixed copper fungicides (copper hydroxide, copper sulfate) applied preventatively before canopy closure.",
      "Biological control agents containing Bacillus subtilis or Bacillus amyloliquefaciens approved by OMRI."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Foliar lesions defoliate more than 20% of the potato canopy before flowering.",
      "Sunken, dark concentric corky lesions appear on harvested tubers."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Potato___Late_blight",
    "name": "Late Blight",
    "crop": "potato",
    "category": "Oomycete",
    "created_at": "2026-09-28T09:00:00Z",
    "image_url": "/images/diseases/Potato___Late_blight.jpg",
    "symptoms_summary": "Rapidly expanding water-soaked lesions with white fungal-like sporulation on leaf undersides.",
    "prevention_summary": "Use certified seed tubers, destroy cull piles early, and monitor regional late blight alerts.",
    "overview": "A destructive water mold (oomycete) infection caused by Phytophthora infestans that can completely defoliate a potato crop within days and rot tubers in storage.",
    "symptoms": [
      "Water-soaked, pale to dark green irregular foliar lesions that rapidly expand.",
      "Dark brown to purplish-black necrotic blotches on foliage and stems.",
      "Delicate white cottony sporulation on the underside of leaves during cool, humid weather."
    ],
    "favourable_conditions": [
      "Cool, humid weather with temperatures between 10\u00b0C and 21\u00b0C (50\u00b0F\u201370\u00b0F).",
      "Relative humidity consistently above 90% with extended foliar wetness exceeding 8 hours."
    ],
    "preventive_measures": [
      "Plant only certified disease-free seed tubers with zero late blight tolerance.",
      "Eliminate all cull piles and destroy volunteer potato plants early in the season.",
      "Monitor regional late blight forecasting warnings and disease severity indices (e.g., BlightCast)."
    ],
    "cultural_management": [
      "Irrigate early in the morning so the foliage dries quickly in the sun.",
      "Hill soil generously around vines to create a barrier preventing washed spores from reaching tubers."
    ],
    "organic_management": [
      "Copper-based fungicides (Bordeaux mixture, copper hydroxide) applied strictly before infection periods under organic certification guidelines.",
      "Approved bio-fungicides applied preventatively as surface protectants."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Immediate alert to agricultural extension upon first visual identification in the district.",
      "Rapid collapse of foliage accompanied by foul odor occurs across multiple field rows."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Potato___healthy",
    "name": "Healthy Foliage",
    "crop": "potato",
    "category": "Healthy",
    "created_at": "2026-09-15T09:00:00Z",
    "image_url": "/images/diseases/Potato___healthy.jpg",
    "symptoms_summary": "Uniform green, intact foliage with active vegetative vigor and no visible lesions.",
    "prevention_summary": "Continue sourcing certified disease-free seed, routine scouting, and balanced drip irrigation.",
    "overview": "Healthy potato plants displaying normal leaf architecture, smooth foliage surfaces, and balanced tuber bulking without infectious pathogens.",
    "symptoms": [
      "Vigorous, uniform green foliage with smooth, intact leaf surfaces.",
      "No concentric rings, water-soaked margins, chlorosis, or necrotic spotting.",
      "Active, balanced vegetative and tuber-bulking development."
    ],
    "favourable_conditions": [
      "Loose, well-aerated sandy loam with optimal pH between 5.5 and 6.5.",
      "Uniform soil moisture management without drought stress or waterlogging."
    ],
    "preventive_measures": [
      "Continue sourcing certified disease-free seed tubers for upcoming planting cycles.",
      "Perform routine field scouting at least twice weekly across field edges and low-lying areas.",
      "Maintain comprehensive soil testing and cover cropping to preserve soil microbiome health."
    ],
    "cultural_management": [
      "Maintain consistent soil moisture through calibrated drip irrigation; avoid drought stress or waterlogging.",
      "Apply balanced fertility based on seasonal soil tests; avoid excess nitrogen that induces overly succulent, disease-prone growth."
    ],
    "organic_management": [
      "No disease treatment required.",
      "Beneficial microbial soil inoculants (e.g., mycorrhizal fungi, Trichoderma) and compost teas may be applied to support natural systemic vigor."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Routine seasonal soil testing to calibrate fertilizer and micronutrient applications.",
      "Integrated Pest Management (IPM) preventative scouting schedule design."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Tomato___Bacterial_spot",
    "name": "Bacterial Spot",
    "crop": "tomato",
    "category": "Bacterial",
    "created_at": "2026-09-18T09:00:00Z",
    "image_url": "/images/diseases/Tomato___Bacterial_spot.jpg",
    "symptoms_summary": "Small, water-soaked dark circular to angular spots on leaves, and scabby raised spots on fruit.",
    "prevention_summary": "Use pathogen-free certified seed, practice 2-year crop rotation, and avoid overhead watering.",
    "overview": "A seed-borne and splash-dispersed bacterial disease caused by Xanthomonas species that infects tomato foliage, blossoms, and developing fruit, causing defoliation and fruit blemishes.",
    "symptoms": [
      "Small (under 3mm), dark brown to black, water-soaked angular leaf spots.",
      "Lesions with greasy appearance, frequently surrounded by yellow chlorotic margins.",
      "Dead centers of spots may drop out, leaving a ragged shot-hole appearance."
    ],
    "favourable_conditions": [
      "Warm temperatures between 24\u00b0C and 30\u00b0C (75\u00b0F\u201386\u00b0F).",
      "High humidity accompanied by wind-driven rain showers or overhead sprinkler irrigation."
    ],
    "preventive_measures": [
      "Use certified disease-free, hot-water-treated seed and disease-free transplants.",
      "Select resistant or tolerant tomato varieties where available.",
      "Rotate out of solanaceous crops (tomato, pepper, eggplant, potato) for a minimum of 2 to 3 years."
    ],
    "cultural_management": [
      "Strictly avoid working, cultivating, or harvesting in fields when foliage is wet.",
      "Use drip irrigation exclusively; eliminate overhead sprinkler irrigation."
    ],
    "organic_management": [
      "Copper bactericides (copper sulfate, copper octanoate) applied preventatively.",
      "Biological bactericides containing Bacillus subtilis or Streptomyces lydicus OMRI-listed formulations."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Severe fruit spotting or blossom abortion reduces harvestable yield significantly.",
      "Copper bactericides fail to arrest disease spread, indicating potential copper resistance."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Tomato___Early_blight",
    "name": "Early Blight",
    "crop": "tomato",
    "category": "Fungal",
    "created_at": "2026-09-20T09:00:00Z",
    "image_url": "/images/diseases/Tomato___Early_blight.jpg",
    "symptoms_summary": "Concentric target-like brown spots on lower leaves with yellow halos, progressing upward.",
    "prevention_summary": "Rotate with non-solanaceous crops, stake plants, prune lower leaves, and use drip irrigation.",
    "overview": "A common fungal disease caused by Alternaria linariae/solani that begins on older bottom leaves and moves up the vine, causing defoliation, stem cankers, and sunscalded fruit.",
    "symptoms": [
      "Small brown-black spots on older, lower foliage that enlarge up to 1/2 inch.",
      "Concentric dark ridges producing a pronounced target-pattern appearance.",
      "Extensive yellowing of surrounding tissue and progressive defoliation from ground level upward."
    ],
    "favourable_conditions": [
      "Warm temperatures between 24\u00b0C and 29\u00b0C (75\u00b0F\u201385\u00b0F).",
      "Frequent rain, heavy dew, or prolonged leaf wetness from overhead watering."
    ],
    "preventive_measures": [
      "3-year crop rotation away from solanaceous plants.",
      "Plant certified disease-free seeds and inspected nursery transplants.",
      "Apply plastic or organic straw mulch around plant bases to block soil-splashed fungal spores."
    ],
    "cultural_management": [
      "Stake, cage, and trellis tomato vines to keep foliage elevated off bare soil.",
      "Prune bottom suckers and lower foliage up to 12-18 inches from the soil line once plants mature."
    ],
    "organic_management": [
      "Copper hydroxide, copper octanoate, or sulfur fungicides applied at the first sign of lower foliar spotting.",
      "Bio-fungicides based on Bacillus amyloliquefaciens or Trichoderma harzianum."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Foliar defoliation progresses rapidly past the mid-canopy before first harvest.",
      "Dark collar-rot lesions girdle the main stem near the soil line."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Tomato___Late_blight",
    "name": "Late Blight",
    "crop": "tomato",
    "category": "Oomycete",
    "created_at": "2026-09-22T09:00:00Z",
    "image_url": "/images/diseases/Tomato___Late_blight.jpg",
    "symptoms_summary": "Large, irregular water-soaked grey-green lesions with white velvety sporulation on leaf undersides.",
    "prevention_summary": "Plant certified clean transplants, maximize air movement, and destroy infected plants promptly.",
    "overview": "A devastating oomycete infection caused by Phytophthora infestans that rapidly attacks leaves, stems, and fruit, causing widespread foliar collapse and firm brown fruit rot.",
    "symptoms": [
      "Large, irregular, water-soaked grayish-green foliar lesions turning brown-black.",
      "Delicate white fungal-like growth visible on the undersides of leaves during high humidity.",
      "Dark brown to black necrotic lesions girdling petioles and main stems."
    ],
    "favourable_conditions": [
      "Cool, damp weather with temperatures between 15\u00b0C and 22\u00b0C (59\u00b0F\u201372\u00b0F).",
      "High relative humidity (>90%) with prolonged leaf wetness exceeding 8 hours."
    ],
    "preventive_measures": [
      "Plant verified late blight-resistant cultivars (e.g., Mountain Magic, Defiant, Plum Regal, Mountain Merit).",
      "Inspect all purchased transplants meticulously before transplanting into field beds.",
      "Eliminate potato cull piles and volunteer tomato and potato plants within 5 miles."
    ],
    "cultural_management": [
      "Maximize row spacing and trellising to facilitate wind penetration and leaf drying.",
      "Water exclusively via drip irrigation lines."
    ],
    "organic_management": [
      "Copper-based fungicides applied strictly preventatively before infection periods under organic protocols.",
      "Organic bio-rationals applied to protect healthy foliage ahead of high-humidity periods."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Immediate notification to local agricultural authorities upon suspected regional late blight outbreak.",
      "Large water-soaked blotches spread rapidly to green fruit and stems."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Tomato___Leaf_Mold",
    "name": "Leaf Mold",
    "crop": "tomato",
    "category": "Fungal",
    "created_at": "2026-09-10T09:00:00Z",
    "image_url": "/images/diseases/Tomato___Leaf_Mold.jpg",
    "symptoms_summary": "Pale green to yellow spots on upper leaf surfaces with olive-green velvety mold underneath.",
    "prevention_summary": "Improve ventilation, reduce relative humidity below 85%, and avoid wetting foliage.",
    "overview": "A foliar fungal disease caused by Passalora fulva (Cladosporium fulvum), common in greenhouses, high tunnels, and humid field settings, causing premature defoliation.",
    "symptoms": [
      "Pale green to light yellow chlorotic patches on the upper surface of older leaves.",
      "Olive-green to grayish-brown velvety fungal mold on the corresponding lower surface.",
      "Leaves curl upwards, wither, and prematurely drop from the plant."
    ],
    "favourable_conditions": [
      "Relative humidity consistently exceeding 85% inside the canopy.",
      "Moderate temperatures between 21\u00b0C and 24\u00b0C (70\u00b0F\u201375\u00b0F)."
    ],
    "preventive_measures": [
      "Grow tomato cultivars bred with specific Cf resistance genes against Passalora fulva.",
      "Maintain relative humidity below 85% in greenhouses and high tunnels.",
      "Sanitize greenhouse interiors, benches, and poly sheets thoroughly between cropping cycles."
    ],
    "cultural_management": [
      "Increase airflow in tunnels using circulation fans and open sidewalls.",
      "Ventilate and heat greenhouses at dusk to prevent condensation on foliage."
    ],
    "organic_management": [
      "Copper fungicides applied thoroughly covering both upper and lower leaf surfaces.",
      "Bio-fungicides containing Bacillus subtilis, Bacillus amyloliquefaciens, or Gliocladium virens."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Velvety mold spreads across more than half of the foliage canopy in protected cultivation.",
      "Cultivars previously bred for leaf mold resistance show breakdown in protection."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Tomato___Septoria_leaf_spot",
    "name": "Septoria Leaf Spot",
    "crop": "tomato",
    "category": "Fungal",
    "created_at": "2026-09-12T09:00:00Z",
    "image_url": "/images/diseases/Tomato___Septoria_leaf_spot.jpg",
    "symptoms_summary": "Numerous small circular spots with greyish-white centres, dark borders, and tiny black fruiting bodies.",
    "prevention_summary": "Remove infected lower foliage, mulch soil to prevent splash dispersal, and practice 3-year crop rotation.",
    "overview": "A widespread foliar fungal disease caused by Septoria lycopersici that starts on the lowest leaves after fruit set and spreads upward, leading to severe defoliation and sunscald.",
    "symptoms": [
      "Numerous circular spots (1/16 to 1/8 inch wide) with dark brown margins and sunken grayish-white centers.",
      "Tiny black specks (pycnidia fruiting bodies) clearly visible inside the gray centers with a hand lens.",
      "Progressive yellowing of surrounding foliage, with lower leaves dying and dropping."
    ],
    "favourable_conditions": [
      "Warm, wet weather with temperatures between 20\u00b0C and 25\u00b0C (68\u00b0F\u201377\u00b0F).",
      "Frequent rainfall or overhead irrigation that splashes fungal spores from the soil onto lower leaves."
    ],
    "preventive_measures": [
      "Rotate out of solanaceous crops for 2 to 3 years.",
      "Thoroughly bury or remove crop debris at the end of the harvest season.",
      "Use plastic, paper, or thick organic straw mulch under plants to prevent soil-to-foliage splash."
    ],
    "cultural_management": [
      "Stake and trellis plants to elevate foliage away from soil moisture.",
      "Prune lower leaves as plants mature to reduce ground-level splash contact."
    ],
    "organic_management": [
      "Fixed copper fungicides applied at the first onset of lower leaf spotting and repeated on a 7-10 day schedule.",
      "Approved biofungicides (Bacillus subtilis, Bacillus amyloliquefaciens)."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Lower and middle foliage defoliates extensively, exposing green fruit to sunburn.",
      "Uncertainty in differentiating small Septoria spots from Bacterial Spot or Early Blight."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Tomato___Spider_mites Two-spotted_spider_mite",
    "name": "Two-Spotted Spider Mite",
    "crop": "tomato",
    "category": "Pest",
    "created_at": "2026-09-14T09:00:00Z",
    "image_url": "/images/diseases/Tomato___Spider_mites_Two-spotted_spider_mite.jpg",
    "symptoms_summary": "Fine yellow stippling on leaves, delicate silken webbing under foliage, and leaf bronzing.",
    "prevention_summary": "Maintain adequate irrigation to avoid drought stress, preserve predatory mites, and scout undersides of leaves.",
    "overview": "An agricultural arachnid pest (Tetranychus urticae) that punctures foliar plant cells to feed on plant sap, causing yellow stippling, webbing, and rapid leaf drying in hot, dusty conditions.",
    "symptoms": [
      "Fine yellow or white stippling and speckling on upper leaf surfaces.",
      "Silky fine webbing visible on the undersides of leaves and at branch junctions.",
      "Leaves turn bronze, dry out, curl, and drop under heavy feeding pressure."
    ],
    "favourable_conditions": [
      "Hot, dry, and dusty weather with temperatures exceeding 30\u00b0C (86\u00b0F).",
      "Drought-stressed plants providing concentrated nutrients to feeding mites."
    ],
    "preventive_measures": [
      "Routinely inspect the undersides of lower leaves using a 10x hand lens.",
      "Control weeds (especially broadleaf weeds like mallow and bindweed) on field edges.",
      "Maintain road dust control around fields (dust deposits inhibit natural predators and trigger mite outbreaks)."
    ],
    "cultural_management": [
      "Provide consistent, adequate soil irrigation to maintain plant vigor.",
      "Use overhead overhead water wash in garden settings to knock down early mite colonies and destroy webbing."
    ],
    "organic_management": [
      "Release biological control predatory mites (Phytoseiulus persimilis, Neoseiulus californicus).",
      "Apply insecticidal soaps, horticultural mineral oils, or neem oil (azadirachtin) ensuring direct contact on leaf undersides."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Silken webbing envelopes terminal growing tips and blossom clusters.",
      "Miticide applications fail to suppress mite populations due to potential chemical resistance."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Tomato___Target_Spot",
    "name": "Target Spot",
    "crop": "tomato",
    "category": "Fungal",
    "created_at": "2026-09-16T09:00:00Z",
    "image_url": "/images/diseases/Tomato___Target_Spot.jpg",
    "symptoms_summary": "Brown circular lesions with concentric rings on leaves and sunken target-like lesions on fruit.",
    "prevention_summary": "Ensure wide row spacing, stake and prune vines for air movement, and avoid prolonged overhead leaf wetness.",
    "overview": "A foliar and fruit fungal disease caused by Corynespora cassiicola that attacks leaves, stems, and ripening tomato fruit in warm, humid subtropical growing conditions.",
    "symptoms": [
      "Small, pinpoint brown water-soaked lesions on older leaves.",
      "Enlarging circular necrotic spots with pale brown centers and dark brown concentric margins.",
      "Lesions may tear or drop out, giving foliage a ragged, shredded appearance."
    ],
    "favourable_conditions": [
      "Warm temperatures between 25\u00b0C and 32\u00b0C (77\u00b0F\u201390\u00b0F).",
      "High relative humidity combined with extended periods of free foliar moisture."
    ],
    "preventive_measures": [
      "Rotate fields away from solanaceous and cucurbit crops for at least 2 years.",
      "Promptly plow under or destroy crop residues immediately after final harvest.",
      "Plant certified disease-free seed and inspect transplants for foliar flecking."
    ],
    "cultural_management": [
      "Trellis plants and maintain wide row spacing to maximize canopy ventilation.",
      "Irrigate using ground drip lines to eliminate foliar wetness."
    ],
    "organic_management": [
      "Preventative copper-based sprays (copper hydroxide, copper octanoate).",
      "Bio-fungicides containing Bacillus amyloliquefaciens strain D747 or Bacillus subtilis."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Sunken concentric lesions appear directly on green or ripening tomato fruit.",
      "Standard protectant fungicides fail to arrest lesion progression across rows."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "name": "Tomato Yellow Leaf Curl Virus (TYLCV)",
    "crop": "tomato",
    "category": "Viral",
    "created_at": "2026-09-08T09:00:00Z",
    "image_url": "/images/diseases/Tomato___Tomato_Yellow_Leaf_Curl_Virus.jpg",
    "symptoms_summary": "Severe upward leaf curling and cupping, marginal chlorosis, stunted bushy plants, and blossom drop.",
    "prevention_summary": "Deploy TYLCV-resistant hybrids, manage whitefly insect vectors with yellow sticky traps, and screen greenhouses.",
    "overview": "A devastating begomovirus transmitted by the sweetpotato/silverleaf whitefly (Bemisia tabaci) that causes severe stunting, erect cupped leaves, and drastic fruit yield reduction.",
    "symptoms": [
      "Marked upward cupping and curling of leaf margins.",
      "Interveinal yellowing (chlorosis) and reduced size of young leaflets.",
      "Significant stunting of plant growth with compact, bushy erect stature."
    ],
    "favourable_conditions": [
      "High whitefly vector populations migrating from nearby infested fields or weed hosts.",
      "Warm, dry climatic conditions that favor rapid whitefly multiplication and flight activity."
    ],
    "preventive_measures": [
      "Plant resistant or tolerant tomato varieties bearing Ty-1, Ty-2, or Ty-3 resistance genes.",
      "Use 50-mesh insect-proof screening in nurseries and high tunnels to exclude whitefly vectors.",
      "Use reflective silver mulches in planting beds to disorient and repel incoming whiteflies."
    ],
    "cultural_management": [
      "Rogue out and destroy infected tomato plants immediately upon symptom detection in sealed plastic bags.",
      "Ensure transplants are 100% whitefly-free before field planting."
    ],
    "organic_management": [
      "Viruses inside plants cannot be cured; management centers strictly on vector suppression.",
      "Deploy yellow sticky cards to monitor and trap whiteflies."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Widespread whitefly swarms accompany sudden widespread plant stunting.",
      "Guidance needed on certified TYLCV-resistant hybrid varieties suited for local growing seasons."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Tomato___Tomato_mosaic_virus",
    "name": "Tomato Mosaic Virus (ToMV)",
    "crop": "tomato",
    "category": "Viral",
    "created_at": "2026-09-06T09:00:00Z",
    "image_url": "/images/diseases/Tomato___Tomato_mosaic_virus.jpg",
    "symptoms_summary": "Light and dark green mosaic mottling, distorted strap-like foliage, and uneven fruit ripening.",
    "prevention_summary": "Plant certified virus-free seed, sanitize hands and tools with milk or soap before handling, and rogue infected plants.",
    "overview": "A highly stable tobamovirus that spreads mechanically through workers' hands, contaminated pruning tools, clothing, and plant debris, causing mottled distorted foliage and internal fruit browning.",
    "symptoms": [
      "Light and dark green mottled mosaic patterns on leaf surfaces.",
      "Distorted, blistered, or narrow strap-like 'fern-leaf' foliage.",
      "Overall plant stunting and reduced vigor."
    ],
    "favourable_conditions": [
      "Frequent mechanical pruning, staking, or harvesting without routine tool disinfection.",
      "Tobacco use near plants or handling foliage with unwashed hands."
    ],
    "preventive_measures": [
      "Plant certified virus-free seed treated with heat or trisodium phosphate (TSP).",
      "Choose tomato hybrids with genetic resistance (carrying Tm-1, Tm-2, or Tm-2^2 resistance genes).",
      "Prohibit tobacco use near tomato production; virus can be transmitted from tobacco products."
    ],
    "cultural_management": [
      "Strict worker sanitation: wash hands thoroughly with warm water and soap or 20% non-fat dry milk solution before handling plants.",
      "Disinfect pruning knives, shears, stakes, and flats in 20% non-fat dry milk or 10% household bleach between plants."
    ],
    "organic_management": [
      "No chemical or organic viricide can cure a virus-infected plant.",
      "Preventative milk sprays (20% non-fat dry milk) during mechanical pruning operations have been shown to reduce mechanical transmission of tobamoviruses."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Mottling and distorted growth appear systematically across young nursery transplant beds.",
      "Confirmation through laboratory immunostrip or ELISA test strips."
    ],
    "content_language": "en"
  },
  {
    "disease_code": "Tomato___healthy",
    "name": "Healthy Foliage",
    "crop": "tomato",
    "category": "Healthy",
    "created_at": "2026-09-01T09:00:00Z",
    "image_url": "/images/diseases/Tomato___healthy.jpg",
    "symptoms_summary": "Lush, uniform green foliage with balanced vegetative growth, strong blossoms, and no lesions.",
    "prevention_summary": "Maintain weekly visual scouting, select disease-resistant varieties, and provide consistent drip irrigation.",
    "overview": "Healthy tomato plants exhibiting vigorous vegetative and reproductive development, clear leaves, and balanced fruit set without infectious pathogens.",
    "symptoms": [
      "Lush, uniform green foliage with balanced vegetative growth.",
      "Leaves free of mosaic mottling, spots, concentric rings, chlorosis, or webbing.",
      "Strong blossom development and uniform fruit set."
    ],
    "favourable_conditions": [
      "Rich, well-draining loamy soil with optimal pH between 6.0 and 6.8.",
      "Full sunlight exposure (6 to 8 hours daily) with good canopy ventilation."
    ],
    "preventive_measures": [
      "Maintain weekly visual scouting across rows and canopy levels.",
      "Select disease-resistant tomato varieties tailored to regional soil and climatic conditions.",
      "Promote biologically active soil through compost additions and balanced cover crops."
    ],
    "cultural_management": [
      "Provide consistent drip irrigation to maintain uniform soil moisture and prevent blossom-end rot.",
      "Ensure balanced fertility based on seasonal soil tests; provide adequate calcium and potassium."
    ],
    "organic_management": [
      "No disease treatment required.",
      "Foliar compost teas, silica sprays, and beneficial root inoculants may be utilized to support systemic plant health."
    ],
    "chemical_treatment": [],
    "chemical_verified": false,
    "consult_expert": [
      "Routine seasonal soil and leaf-tissue nutrient testing to optimize fruit production.",
      "Preventative Integrated Pest Management (IPM) monitoring schedule setup."
    ],
    "content_language": "en"
  }
];

const toListItem = (d) => d;

// ---- Router ----
const respond = (config, status, data) => {
  const response = { data, status, statusText: String(status), headers: {}, config, request: {} };
  if (status < 400) return Promise.resolve(response);
  const msg = typeof data?.detail === 'string' ? data.detail : `Request failed with status ${status}`;
  return Promise.reject(new AxiosError(msg, status >= 500 ? 'ERR_BAD_RESPONSE' : 'ERR_BAD_REQUEST', config, {}, response));
};

const parseBody = (config) => {
  if (typeof config.data === 'string') {
    try {
      return JSON.parse(config.data);
    } catch {
      return {};
    }
  }
  return config.data || {};
};

const nameFromEmail = (email) => {
  const local = (email.split('@')[0] || 'Farmer').replace(/[._-]+/g, ' ');
  return local.replace(/\b\w/g, (c) => c.toUpperCase());
};

const handler = async (config) => {
  const method = (config.method || 'get').toLowerCase();
  const url = (config.url || '').replace(/\?.*$/, '');
  await sleep(250 + Math.random() * 350);

  // ---- auth ----
  if (url === '/auth/me' && method === 'get') {
    const user = read(SESSION_KEY, null);
    return user ? respond(config, 200, user) : respond(config, 401, { detail: 'Not authenticated' });
  }
  if (url === '/auth/login' && method === 'post') {
    const { email, password } = parseBody(config);
    if (!email || !password) return respond(config, 422, { detail: 'Email and password are required' });
    const users = read(USERS_KEY, {});
    const key = email.toLowerCase();
    write(SESSION_KEY, { id: 'preview-user', name: users[key] || nameFromEmail(email), email });
    return respond(config, 200, { success: true });
  }
  if (url === '/auth/register' && method === 'post') {
    const { name, email } = parseBody(config);
    const users = read(USERS_KEY, {});
    users[String(email).toLowerCase()] = name;
    write(USERS_KEY, users);
    return respond(config, 201, { success: true }); // no auto-login, so the "please sign in" flow is visible
  }
  if (url === '/auth/logout' && method === 'post') {
    write(SESSION_KEY, null);
    return respond(config, 204, null);
  }

  // everything below needs a session
  if (!read(SESSION_KEY, null)) return respond(config, 401, { detail: 'Not authenticated' });

  // ---- preferences ----
  if (url === '/users/me/preferences') {
    if (method === 'put') {
      const prefs = { ...read('afa.preview.prefs', {}), ...parseBody(config) };
      write('afa.preview.prefs', prefs);
      return respond(config, 200, prefs);
    }
    return respond(config, 200, read('afa.preview.prefs', {}));
  }

  // ---- diseases ----
  if (url === '/diseases' && method === 'get') {
    return respond(config, 200, { items: DISEASES.map(toListItem) });
  }
  const diseaseMatch = url.match(/^\/diseases\/(.+)$/);
  if (diseaseMatch && method === 'get') {
    const raw = decodeURIComponent(diseaseMatch[1]);
    const norm = (c) => c.toLowerCase().replace(/[\s_-]+/g, '_');
    const found = DISEASES.find((d) => d.disease_code === raw || norm(d.disease_code) === norm(raw));
    return found ? respond(config, 200, found) : respond(config, 404, { detail: 'Disease not found' });
  }

  // ---- predict (SAMPLE OUTPUT - not a model result) ----
  if (url === '/predict' && method === 'post') {
    await sleep(1200);
    const file = config.data?.get?.('image');
    const seed = file?.size || 1;
    const d = DISEASES[seed % DISEASES.length];
    const confidence = Math.round((0.55 + (seed % 43) / 100) * 100) / 100; // 0.55 - 0.97, sometimes low
    const record = {
      analysis_id: `preview-${Date.now()}`,
      crop: d.crop,
      disease_code: d.disease_code,
      disease: d.name,
      confidence,
      created_at: new Date().toISOString(),
      image_url: null,
    };
    write(HISTORY_KEY, [record, ...read(HISTORY_KEY, [])]);
    return respond(config, 200, {
      success: true,
      ...record,
      treatment: {
        summary: d.overview,
        preventive_measures: d.preventive_measures,
        organic_treatment: d.organic_management,
        chemical_treatment: [],
      },
      model_version: 'ui-preview (sample output, not a real prediction)',
    });
  }

  // ---- history ----
  if (url === '/history' && method === 'get') {
    const p = config.params || {};
    let items = read(HISTORY_KEY, []);
    const byDisease = new Map();
    items.forEach((r) => {
      const e = byDisease.get(r.disease_code) || { disease_code: r.disease_code, disease: r.disease, count: 0 };
      e.count += 1;
      byDisease.set(r.disease_code, e);
    });
    const summary = { by_disease: [...byDisease.values()] };
    const q = (p.search || '').toLowerCase();
    if (q) items = items.filter((r) => r.disease.toLowerCase().includes(q));
    if (p.crop) items = items.filter((r) => r.crop === p.crop);
    if (p.date_from) items = items.filter((r) => r.created_at.slice(0, 10) >= p.date_from);
    if (p.date_to) items = items.filter((r) => r.created_at.slice(0, 10) <= p.date_to);
    items = [...items].sort((a, b) => (p.sort === 'oldest' ? 1 : -1) * (new Date(b.created_at) - new Date(a.created_at)));
    const pageSize = Number(p.page_size) || 12;
    const page = Number(p.page) || 1;
    return respond(config, 200, {
      items: items.slice((page - 1) * pageSize, page * pageSize),
      total: items.length,
      page,
      page_size: pageSize,
      summary,
    });
  }
  const historyDeleteMatch = url.match(/^\/history\/(.+)$/);
  if (historyDeleteMatch && method === 'delete') {
    const idToDelete = decodeURIComponent(historyDeleteMatch[1]);
    const items = read(HISTORY_KEY, []);
    const updated = items.filter((r) => String(r.analysis_id || r.id) !== idToDelete);
    write(HISTORY_KEY, updated);
    return respond(config, 200, {
      success: true,
      message: 'Analysis record deleted successfully.',
      analysis_id: idToDelete,
    });
  }

  return respond(config, 404, { detail: `Preview mode has no handler for ${method.toUpperCase()} ${url}` });
};

apiClient.defaults.adapter = handler;
