import { SlidersHorizontal } from "lucide-react";
import { useState } from "react";

import {
  SearchFiltersContent,
  type SearchFiltersProps,
} from "@/components/gyms/SearchFiltersContent";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

export function SearchFilters(props: SearchFiltersProps) {
  const [open, setOpen] = useState(false);

  // モバイルで「検索」ボタンを押したらSheetを閉じる
  const handleSubmitSearch = () => {
    props.onSubmitSearch();
    setOpen(false);
  };

  return (
    <>
      {/* Desktop View */}
      <div className="hidden lg:block">
        <SearchFiltersContent {...props} />
      </div>

      {/* Mobile View (Sheet) */}
      <div className="lg:hidden">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button className="w-full gap-2" variant="outline">
              <SlidersHorizontal className="h-4 w-4" />
              検索条件を変更
            </Button>
          </SheetTrigger>
          <SheetContent className="w-full overflow-y-auto sm:max-w-lg" side="bottom">
            <SheetHeader className="mb-4">
              <SheetTitle>検索条件</SheetTitle>
            </SheetHeader>
            <SearchFiltersContent
              {...props}
              className="border-none p-0 shadow-none"
              onSubmitSearch={handleSubmitSearch}
            />
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
