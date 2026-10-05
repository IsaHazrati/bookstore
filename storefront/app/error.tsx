"use client";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <>
      <h1>مشکلی پیش آمد</h1>
      <p className="muted">دریافت اطلاعات با خطا مواجه شد. چند لحظه بعد دوباره تلاش کنید.</p>
      <button onClick={reset}>تلاش مجدد</button>
    </>
  );
}
