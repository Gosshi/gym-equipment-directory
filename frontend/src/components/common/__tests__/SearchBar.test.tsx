import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { vi } from "vitest";

import { SearchBar } from "@/components/common/SearchBar";

describe("SearchBar", () => {
  it("renders the label and input, and forwards change events", async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    function ControlledSearchBar() {
      const [value, setValue] = useState("ベンチ");

      return (
        <SearchBar
          id="keyword"
          label="キーワード"
          onChange={nextValue => {
            setValue(nextValue);
            handleChange(nextValue);
          }}
          placeholder="施設名やカテゴリで検索"
          value={value}
        />
      );
    }

    render(<ControlledSearchBar />);

    const input = screen.getByLabelText("キーワード");
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue("ベンチ");

    await user.type(input, "プレス");

    expect(input).toHaveValue("ベンチプレス");
    expect(handleChange).toHaveBeenCalled();
    expect(handleChange).toHaveBeenLastCalledWith("ベンチプレス");
  });

  it("renders any helper content passed as children", () => {
    render(
      <SearchBar id="gym-search" label="検索" onChange={() => {}} value="">
        <p role="note">候補は2文字以上で表示されます</p>
      </SearchBar>,
    );

    expect(screen.getByRole("note")).toHaveTextContent("候補は2文字以上で表示されます");
  });
});
