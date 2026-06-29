import { Suspense } from "react";
import ActivityPage from "@/components/ActivityPage";

export default function Activity() {
  return (
    <Suspense>
      <ActivityPage />
    </Suspense>
  );
}
