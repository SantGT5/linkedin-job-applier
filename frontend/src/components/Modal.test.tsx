import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import Modal from "./Modal";

function TwoStep() {
  const [step, setStep] = useState<"first" | "second" | "none">("first");
  if (step === "first") return <Modal title="First" onClose={() => setStep("second")}><button>Inside first</button></Modal>;
  if (step === "second") return <Modal title="Second" role="alertdialog" onClose={() => setStep("none")}><button>Yes</button></Modal>;
  return null;
}

test("closing by the backdrop lets the next dialog keep focus", async () => {
  render(<TwoStep />);
  const backdrop = screen.getByRole("dialog").parentElement!;
  await userEvent.click(backdrop);
  expect(await screen.findByRole("alertdialog")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Yes" })).toHaveFocus();
});
