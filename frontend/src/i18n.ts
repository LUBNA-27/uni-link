/**
 * Minimal EN/AR i18n. The English sentence IS the key: t('Find my ride').
 * A missing Arabic entry falls back to English (run `node scripts/check-i18n.mjs` to list gaps).
 * Server-sent free text (messages, reasons, landmarks) is displayed as received: the client sends
 * `Accept-Language: ar|en`, and the backend may localize it (see CONTRACT_FOR_RANAD.md).
 * Money is never translated: only the currency label changes (JOD → د.أ); fils are integers.
 */
export type Lang = 'en' | 'ar'

function initial(): Lang {
  try {
    const q = new URLSearchParams(window.location.search).get('lang')
    if (q === 'ar' || q === 'en') return q
    const saved = localStorage.getItem('uni.lang')
    if (saved === 'ar' || saved === 'en') return saved
    if (navigator.language?.toLowerCase().startsWith('ar')) return 'ar'
  } catch { /* ignore */ }
  return 'en'
}

let current: Lang = initial()
export const getLang = (): Lang => current
export function applyLang(l: Lang) {
  current = l
  try { localStorage.setItem('uni.lang', l) } catch { /* private mode */ }
  document.documentElement.lang = l
  document.documentElement.dir = l === 'ar' ? 'rtl' : 'ltr'
}
applyLang(current)

export type Vars = Record<string, string | number>
export function tr(en: string, vars?: Vars, lang: Lang = current): string {
  let s = lang === 'ar' ? (AR[en] ?? en) : en
  if (vars) for (const k of Object.keys(vars)) s = s.replaceAll(`{${k}}`, String(vars[k]))
  return s
}
/** For temporary mocks only: pick the string for the current language. */
export const pick = (en: string, ar: string) => (current === 'ar' ? ar : en)

export const currency = (lang: Lang = current) => (lang === 'ar' ? 'د.أ' : 'JOD')

const AR: Record<string, string> = {
  /* shell */
  'Schedule': 'الجدول', 'Trip': 'الرحلة', 'Journey': 'المسار', 'Pass': 'التذكرة', 'Insights': 'الإحصاءات',
  'Progress': 'التقدّم', 'Language': 'اللغة',
  'Campus Commute · prototype': 'التنقّل الجامعي · نموذج أولي',
  'Demo build: some screens use temporary MOCK data (not the real engine yet).':
    'نسخة تجريبية: بعض الشاشات تستخدم بيانات MOCK مؤقتة (ليست من المحرك الحقيقي بعد).',
  'UniLink — hackathon prototype, simulation data.': 'UniLink — نموذج أولي للهاكاثون، بيانات محاكاة.',
  'Simulation controls': 'أدوات المحاكاة',
  'Simulation data · live engine': 'بيانات محاكاة · المحرك الحقيقي',
  'MOCK data · not the engine': 'بيانات MOCK · ليست من المحرك',
  'Simulation data = fictional riders and cars computed by the real engine. MOCK = a temporary canned reply, not computed.':
    'بيانات المحاكاة = ركّاب وسيارات وهمية يحسبها المحرك الحقيقي. MOCK = ردّ جاهز مؤقت ولم يُحسب.',
  'You are offline. Check your connection, then try again.': 'لا يوجد اتصال بالإنترنت. تحقق من الاتصال ثم أعد المحاولة.',
  'Try again': 'أعد المحاولة', 'code: {c}': 'الرمز: {c}', 'Close': 'إغلاق',

  /* schedule */
  'Your timetable, once.': 'جدولك، مرة واحدة.',
  'Upload a photo of your semester timetable. We read it, you check it, and every trip after that is a single tap.':
    'ارفع صورة جدول الفصل. نقرأه نحن وتراجعه أنت، وبعدها كل رحلة بلمسة واحدة.',
  'Upload timetable photo': 'رفع صورة الجدول', 'Enter classes manually': 'إدخال المحاضرات يدوياً',
  'Your photo is only used to read the classes; the API contract says it is not kept by default.':
    'الصورة تُستخدم فقط لقراءة المحاضرات، وبحسب العقد التقني لا تُحفظ افتراضياً.',
  'Add your classes': 'أضف محاضراتك', 'Check your timetable': 'راجع جدولك',
  'Add each weekly class. You will review them next.': 'أضف كل محاضرة أسبوعية، وستراجعها في الخطوة التالية.',
  'Fix anything we got wrong. Highlighted fields need a quick look.': 'صحّح أي خطأ. الحقول المظللة تحتاج نظرة سريعة.',
  'Read by Gemini Vision': 'قُرئ بواسطة Gemini Vision', 'Entered manually': 'أُدخل يدوياً', 'Fixture timetable (demo)': 'جدول تجريبي (عرض)',
  'Course (e.g. CS 201)': 'المساق (مثال: CS 201)', 'Room': 'القاعة', 'Course': 'المساق', 'Day': 'اليوم', 'Start time': 'وقت البداية',
  'Remove class': 'حذف المحاضرة', 'Timetable photo': 'صورة الجدول', 'Looks right': 'صحيح',
  'Add a class': 'إضافة محاضرة', 'Check my classes': 'تحقق من محاضراتي', 'Confirm timetable': 'تأكيد الجدول',
  'Check {n} highlighted field first': 'راجع الحقل المظلّل ({n}) أولاً',
  'Check {n} highlighted fields first': 'راجع الحقول المظلّلة ({n}) أولاً', 'Start over': 'ابدأ من جديد',
  'Sun': 'الأحد', 'Mon': 'الاثنين', 'Tue': 'الثلاثاء', 'Wed': 'الأربعاء', 'Thu': 'الخميس',
  'Sunday': 'الأحد', 'Monday': 'الاثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء', 'Thursday': 'الخميس',

  /* trip */
  'Irbid East → JUST': 'إربد الشرقية ← جامعة العلوم والتكنولوجيا', 'Irbid Nuzha → JUST': 'إربد النزهة ← جامعة العلوم والتكنولوجيا',
  'Sweileh → AAU': 'صويلح ← جامعة عمّان الأهلية',
  'Plan your ride': 'خطّط لرحلتك', 'Door-to-Door to campus, shared fairly. Tell us what matters.': 'من الباب إلى الجامعة، وبتقسيم عادل. أخبرنا بما يهمّك.',
  'Where from?': 'من أين؟', 'No classes on Fridays and Saturdays': 'لا محاضرات يومي الجمعة والسبت',
  'No classes saved for {d}. Go back and add one to your timetable.': 'لا توجد محاضرات محفوظة ليوم {d}. ارجع وأضف واحدة إلى جدولك.',
  'Which class are you riding for?': 'لأي محاضرة تريد الرحلة؟', 'Arrive before class': 'الوصول قبل المحاضرة',
  'Your deadline is calculated by the server from this.': 'يحسب الخادم موعدك النهائي من هذه القيمة.', '{m} minutes': '{m} دقائق',
  'Default': 'افتراضي', 'Door-to-Door pickup': 'الاستلام من الباب إلى الباب', 'Never relaxed': 'لا يُتساهل فيها أبداً',
  'Who can ride with you': 'من يمكنه مرافقتك', 'Female-only': 'نساء فقط', 'Male-only': 'رجال فقط',
  'I use a wheelchair': 'أستخدم كرسياً متحركاً', 'Only ramp vehicles are offered. If none, we say so — never a car without a ramp.':
    'نعرض فقط سيارات مزوّدة بمنحدر. وإن لم تتوفر نخبرك بذلك، ولا نعرض أبداً سيارة بلا منحدر.',
  'I need a Big Car': 'أحتاج سيارة كبيرة', 'Extra space for equipment.': 'مساحة إضافية للمعدّات.',
  'Max 4 riders per car and your arrival deadline are always enforced.': 'الحد الأقصى 4 ركّاب في السيارة وموعد وصولك دائماً مضمونان.',
  'Can be flexible (Best Deal)': 'يمكن المرونة فيها (أفضل صفقة)', 'Companions: {n}': 'المرافقون: {n}', 'Companions: 0 (ride alone)': 'المرافقون: 0 (رحلة منفردة)',
  'If no exact match, Best Deal relaxes ONE of these at a time.': 'إذا لم نجد مطابقة تامة، تخفّف «أفضل صفقة» واحداً فقط من هذه في كل مرة.',
  'Preferred pickup time': 'وقت الاستلام المفضّل', 'Fare cap (JOD)': 'الحد الأعلى للأجرة (دينار)',
  'Max your share: JOD {x}. You approve every price increase.': 'أقصى حصة لك: {x} دينار. وأنت توافق على كل زيادة في السعر.',
  'Share the ride': 'مشاركة الرحلة', 'Required to split the fare with same-pool students.': 'مطلوبة لتقسيم الأجرة مع طلاب من المجموعة نفسها.',
  'Find my ride': 'ابحث عن رحلتي', 'Turn on “Share the ride” to find shared options.': 'فعّل «مشاركة الرحلة» لإيجاد خيارات مشتركة.',
  'Running late?': 'متأخر؟', 'Emergency mode looks for a trip already on the road. Price changes apply to you only.':
    'وضع الطوارئ يبحث عن رحلة تسير الآن. تغيّر السعر ينطبق عليك أنت فقط.',
  'It is now (simulated)': 'الوقت الآن (محاكاة)', 'Find me a ride now': 'ابحث لي عن رحلة الآن', 'Emergency ride': 'رحلة طوارئ',
  'Approve · JOD {x}': 'موافقة · {x} دينار',
  'A standard solo ride may be possible, but it is only a simulated hand-off and may be above your fare cap. Nothing is dispatched or booked.':
    'قد تتوفر رحلة عادية منفردة، لكنها تحويل محاكى فقط وقد تتجاوز الحد الأعلى للأجرة. لا يُرسَل شيء ولا يُحجز.',

  /* journey */
  'No journey yet': 'لا توجد رحلة بعد', 'Tell us about your trip first.': 'أخبرنا عن رحلتك أولاً.', 'Plan a ride': 'خطّط لرحلة',
  'Edit request': 'تعديل الطلب', 'Class {c} · {n} companions · cap {x} JOD': 'محاضرة {c} · {n} مرافقين · الحد {x} دينار',
  'This plan is out of date.': 'هذه الخطة لم تعد محدّثة.', 'Refresh': 'تحديث',
  'Exact match found': 'وجدنا مطابقة تامة', 'Everything you asked for, as requested.': 'كل ما طلبته، كما طلبته.',
  'EXACT MATCH': 'مطابقة تامة', 'Review & confirm': 'مراجعة وتأكيد',
  'No exact match — here is your Best Deal': 'لا توجد مطابقة تامة — هذه أفضل صفقة لك',
  'Your safety and accessibility rules stay. We relax exactly one flexible thing at a time.':
    'قواعد السلامة وإمكانية الوصول تبقى كما هي. نخفّف شيئاً مرناً واحداً فقط في كل مرة.',
  'Nothing is booked or charged until you confirm.': 'لا يُحجز ولا يُخصم أي شيء حتى تؤكّد.',
  'No accessible vehicle right now': 'لا توجد سيارة مهيّأة متاحة حالياً', 'No route fits yet': 'لا يوجد مسار مناسب بعد',
  'We could not find a route that meets every rule you set.': 'لم نجد مساراً يحقق كل القواعد التي حدّدتها.',
  'Change my request': 'تعديل طلبي', 'Looking for your ride…': 'نبحث عن رحلتك…',
  'Your strict request': 'طلبك الصارم', '0 exact matches for what you asked': 'لا توجد مطابقة تامة لما طلبت',
  'Relaxing exactly one flexible thing…': 'نخفّف شيئاً مرناً واحداً فقط…',
  'We never show a car without a ramp, and we never relax who can ride with you.': 'لا نعرض أبداً سيارة بلا منحدر، ولا نتساهل في من يرافقك.',
  'What we did not relax': 'ما لم نتساهل فيه', 'Your accessibility need': 'احتياجك لإمكانية الوصول', 'Your ride pool': 'مجموعة الرحلة',
  'Simulated operator assistance': 'مساعدة موظف (محاكاة)', 'reason code: {c}': 'رمز السبب: {c}',

  /* confirm / booked */
  'Confirm your ride': 'تأكيد رحلتك', 'You will pay': 'ستدفع', 'Jeeny Wallet balance now': 'رصيد محفظة Jeeny الآن',
  'I understand this is a simulated booking. No real payment is made and no real car is dispatched.':
    'أفهم أن هذا حجز محاكى. لا يوجد دفع حقيقي ولا تُرسل سيارة حقيقية.',
  'See the updated plan': 'عرض الخطة المحدّثة', 'Confirm · pay {x} from Wallet': 'تأكيد · ادفع {x} من المحفظة',
  'You are booked': 'تم حجزك', 'No active trip': 'لا توجد رحلة نشطة',
  'Show this pass to your driver. Simulation only — no real car is dispatched.': 'اعرض هذه التذكرة على السائق. محاكاة فقط — لا تُرسل سيارة حقيقية.',
  'Book a ride to see your boarding pass here.': 'احجز رحلة لتظهر تذكرة الصعود هنا.',
  'Sim clock {t}': 'ساعة المحاكاة {t}', 'AWAITING CONSENT': 'بانتظار الموافقات', 'BOOKED': 'محجوزة', 'Paid so far: {x}': 'المدفوع حتى الآن: {x}',
  'My first class was canceled': 'تم إلغاء محاضرتي الأولى', 'Jeeny Wallet (simulated)': 'محفظة Jeeny (محاكاة)',
  'We will use your saved timetable to find your next class. Nothing changes until you approve.': 'سنستخدم جدولك المحفوظ لإيجاد محاضرتك التالية. لا يتغيّر شيء حتى توافق.',
  'Find my next class': 'ابحث عن محاضرتي التالية', 'Switch to my {c} class': 'انتقل إلى محاضرة {c}',
  'Cancel this trip and get {x} back. {terms}': 'ألغِ هذه الرحلة واسترجع {x}. {terms}', 'Cancel this trip': 'إلغاء هذه الرحلة', 'Keep my trip': 'إبقاء رحلتي',
  'Trip canceled.': 'أُلغيت الرحلة.',
  'This proposal changed while you were deciding. We refreshed it — please review it again.': 'تغيّر هذا الاقتراح أثناء تفكيرك. حدّثناه — يرجى مراجعته من جديد.',
  'Class shifted. Your old seat was released.': 'تم نقل المحاضرة. وتم تحرير مقعدك القديم.',
  'Updated. Your wallet and trip are up to date.': 'تم التحديث. المحفظة والرحلة محدّثتان.',
  'Thanks — waiting for the other riders to agree. You are not charged until everyone does.': 'شكراً — بانتظار موافقة بقية الركّاب. لن يُخصم منك شيء حتى يوافق الجميع.',
  'Ledger': 'سجل الحركات', 'Wallet ledger': 'سجل المحفظة',

  /* pass / cards */
  'BOARDING PASS': 'تذكرة الصعود', 'REVIEW': 'مراجعة', 'TRIP {id}': 'رحلة {id}', 'Door-to-Door → Campus': 'من الباب إلى الجامعة',
  'Arrive': 'الوصول', 'deadline {t}': 'الموعد النهائي {t}', 'Your share': 'حصتك', 'of {x} vehicle total': 'من إجمالي السيارة {x}', 'fils': 'فلس',
  'Leave home {t}': 'المغادرة من المنزل {t}', 'Pickup order': 'ترتيب الاستلام', 'Your pickup': 'استلامك', 'Companion pickup {n}': 'استلام مرافق {n}',
  'Campus drop-off': 'النزول عند الجامعة',
  'Fair split · each pays for the distance they ride': 'تقسيم عادل · كلٌّ يدفع مقابل المسافة التي يقطعها', 'You': 'أنت',
  'Vehicle total {x} = what the shares add up to (server-computed).': 'إجمالي السيارة {x} = مجموع الحصص (محسوب في الخادم).',
  'Accessible drop-off: {l}': 'نزول مهيّأ: {l}', 'Source: {s} · verified': 'المصدر: {s} · موثّق', 'Source: {s} · NOT verified — confirm with campus': 'المصدر: {s} · غير موثّق — تأكّد من الجامعة',
  'Hypothetical reference: the same route with 4 riders would cost {x} — an illustration, not an available quote.': 'مرجع افتراضي: المسار نفسه بأربعة ركّاب كان سيكلّف {x} — للتوضيح فقط وليس عرضاً متاحاً.',
  'Your difference: {x}.': 'الفرق بالنسبة لك: {x}.',
  'Safety and accessibility filters never relaxed': 'مرشّحات السلامة وإمكانية الوصول لا يُتساهل فيها',
  'BEST DEAL {n}': 'أفضل صفقة {n}', ' · TOP PICK': ' · الأفضل', 'score {s}': 'التقييم {s}',
  'What we relaxed (one thing only)': 'ما خفّفناه (شيء واحد فقط)', 'Nothing — exact match': 'لا شيء — مطابقة تامة',
  'leave home {t}': 'المغادرة {t}', 'Matches the reference': 'تطابق المرجع', '{x} vs reference': '{x} مقارنة بالمرجع',
  'Reference {x} = hypothetical same-route 4-rider price, not an available quote.': 'المرجع {x} = سعر افتراضي لنفس المسار بأربعة ركّاب، وليس عرضاً متاحاً.',
  'See the fair split': 'عرض التقسيم العادل', 'Choose this · {x}': 'اختر هذا · {x}',
  'What we relaxed': 'ما خفّفناه',

  /* proposals */
  'SMART RESCUE': 'الإنقاذ الذكي', 'CLASS SHIFT': 'نقل المحاضرة', 'EMERGENCY RIDE': 'رحلة طوارئ', 'Needs your OK': 'تحتاج موافقتك',
  'Next class from your saved timetable': 'المحاضرة التالية من جدولك المحفوظ', 'No new photo scan was needed.': 'لم نحتج إلى مسح صورة جديدة.',
  'leave {t}': 'المغادرة {t}', 'was {x}': 'كانت {x}',
  'Old booking refunded': 'استرجاع الحجز القديم', 'New booking charged': 'خصم الحجز الجديد', 'Net change': 'صافي التغيّر',
  'Emergency pricing applies to you only. Riders already on this trip keep the same fare and their arrival time.': 'سعر الطوارئ ينطبق عليك أنت فقط. أما الركّاب الموجودون فيحتفظون بالأجرة نفسها ووقت وصولهم.',
  'Everyone affected must agree (simulated riders)': 'يجب أن يوافق كل المتأثرين (ركّاب محاكون)', 'pending': 'بالانتظار', 'accepted': 'وافق', 'declined': 'رفض',
  'Other options (not bookable under your fare cap)': 'خيارات أخرى (لا يمكن حجزها ضمن حدّك الأعلى)',
  'Raising your cap is a separate change you must make yourself.': 'رفع الحد الأعلى تغيير منفصل عليك أن تجريه بنفسك.',
  'You approved. Waiting for the other riders — nobody is charged until all agree.': 'وافقت. بانتظار بقية الركّاب — لن يُخصم من أحد حتى يوافق الجميع.',
  'Approve': 'موافقة', 'Keep my current booking': 'إبقاء حجزي الحالي', 'No thanks': 'لا، شكراً', 'Decline': 'رفض',

  /* insights */
  'Fleet insights': 'إحصاءات الأسطول', 'Computed by the backend from the simulation fixtures. Fictional riders, not real users.': 'يحسبها الخادم من بيانات المحاكاة. ركّاب وهميون وليسوا مستخدمين حقيقيين.',
  'No numbers yet': 'لا توجد أرقام بعد',
  'This page shows only figures the backend actually computes. The /api/insights endpoint is not connected yet, so nothing is shown rather than made-up numbers.':
    'تعرض هذه الصفحة فقط ما يحسبه الخادم فعلاً. نقطة /api/insights غير موصولة بعد، لذلك لا نعرض شيئاً بدل عرض أرقام مختلقة.',
  'n = {n}': 'العدد = {n}', 'Generated {t}': 'أُنشئ {t}', 'Back to the app': 'العودة إلى التطبيق', 'Loading insights…': 'جارٍ تحميل الإحصاءات…',

  /* flags & server-style labels */
  'CAP_EXCEEDED_REQUIRES_APPROVAL': 'يتجاوز الحد الأعلى · يحتاج موافقة', 'LATE_ARRIVAL': 'وصول متأخر', 'NO_RAMP': 'بلا منحدر',
  'ACCESSIBILITY_UNVERIFIED': 'إمكانية الوصول غير موثّقة',
  'Same-gender pool': 'مجموعة من الجنس نفسه', 'Capacity ≤ 4': 'السعة ≤ 4', 'Meets class deadline': 'يلتزم بموعد المحاضرة',
  'Wheelchair-accessible vehicle': 'سيارة مهيّأة للكرسي المتحرك', 'Female-only trip': 'رحلة للنساء فقط', 'Free seat available': 'يوجد مقعد شاغر',
  'Everyone still meets their deadline': 'الجميع ما زالوا يصلون في موعدهم',
  'Standard car · 4 seats': 'سيارة عادية · 4 مقاعد', 'WAV-01 · ramp vehicle': 'WAV-01 · سيارة بمنحدر', 'En-route trip TRP-0002': 'رحلة جارية TRP-0002',
  'Your door · Irbid East (synthetic)': 'باب منزلك · إربد الشرقية (وهمي)', 'Companion B · Irbid East (synthetic)': 'المرافقة B · إربد الشرقية (وهمي)',
  'Companion C · Irbid East (synthetic)': 'المرافقة C · إربد الشرقية (وهمي)', 'Replacement rider D · Irbid East (synthetic)': 'الراكبة البديلة D · إربد الشرقية (وهمي)',
  'Companion · Irbid East (synthetic)': 'مرافقة · إربد الشرقية (وهمي)', 'Nearest road to your door (synthetic)': 'أقرب شارع لباب منزلك (وهمي)',
  'Ramp-accessible pickup · Sweileh (synthetic)': 'استلام مهيّأ بمنحدر · صويلح (وهمي)',
  'Companion B (simulated)': 'المرافقة B (محاكاة)', 'Replacement rider D (simulated)': 'الراكبة البديلة D (محاكاة)',
  'Ramp-equipped campus entrance (demo)': 'مدخل الجامعة المزوّد بمنحدر (عرض)', 'MOCK · simulation fixture, not a verified campus fact': 'MOCK · بيانات محاكاة وليست حقيقة موثّقة عن الجامعة',
  'companions 3→2': 'المرافقات 3 ← 2', 'departure −10 min': 'المغادرة قبل 10 دقائق',
  /* round 2 */
  'Simulation data = the engine is real, the world is simulated. MOCK = a temporary stand-in, not the engine.':
    'بيانات محاكاة = المحرك حقيقي والعالم محاكى. MOCK = بديل مؤقت وليس المحرك.',
  'Fleet Insights': 'إحصاءات الأسطول', 'Best Deal option {n}': 'خيار أفضل صفقة {n}', 'TOP PICK': 'الأفضل',
  'Choose this': 'اختاري هذا', '{x} proposal': 'اقتراح {x}', 'Group consent': 'موافقة المجموعة',
  'Options above your fare cap': 'خيارات فوق سقف أجرتك', 'TRIP': 'الرحلة', 'Paid so far:': 'المدفوع حتى الآن:',
  'Switch to my {x} class': 'التبديل إلى محاضرتي الساعة {x}', 'next': 'التالية',
  'Cancel this trip and get': 'ألغِ هذه الرحلة واسترجع', 'back.': 'دينار.',
  'Yes': 'نعم', 'No': 'لا',
  'Numbers the engine computed from this simulated session.': 'أرقام حسبها المحرك من هذه الجلسة المحاكاة.',
  'Loading…': 'جارٍ التحميل…',
  'Insights appear once the live engine is connected. We never show made-up statistics here.':
    'تظهر الإحصاءات بعد ربط المحرك الحقيقي. لا نعرض هنا أي أرقام مختلقة.',
  'Basis: {b}': 'الأساس: {b}', 'Simulation data': 'بيانات محاكاة',
  'Checking safety and accessibility rules first, then the best route.': 'نتحقق من قواعد الأمان وإمكانية الوصول أولاً ثم نختار أفضل مسار.',
  'This usually takes a moment.': 'عادةً يستغرق لحظات.',
  "We couldn't get your plan": 'تعذّر الحصول على خطتك', 'Nothing was booked or charged.': 'لم يُحجز ولم يُخصم أي شيء.',
  'Exact match: none found': 'مطابقة تامة: لم نجد',
  'Relaxing one flexible thing, keeping every safety rule…': 'نخفّف شرطاً مرناً واحداً مع الإبقاء على كل قواعد الأمان…',
  'We never relax gender pool, wheelchair or ramp requirements, or your fare cap — even to find you a ride.':
    'لا نخفّف أبداً شرط الجنس أو الكرسي المتحرك أو المنحدر أو سقف الأجرة — حتى لو لم نجد رحلة.',
  'Check {n} highlighted field(s) first': 'راجع الحقول المظلّلة ({n}) أولاً',
  'Max your share: {x}. You approve every price increase.': 'أقصى حصة لك: {x}. وأنت توافق على كل زيادة في السعر.',
}
export const AR_KEYS = Object.keys(AR)
