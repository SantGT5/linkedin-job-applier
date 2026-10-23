import Modal from "./Modal";

export default function ConfirmSentDialog({ email, busy, onYes, onNo }: { email: string; busy: boolean; onYes: () => void; onNo: () => void }) {
  return (
    <Modal title="Did you send it?" role="alertdialog" onClose={onNo} width="max-w-md">
      <div className="px-5 py-5">
        <p className="text-lg font-semibold" aria-hidden="true">
          Did you send it?
        </p>
        <p className="mt-1 text-sm text-muted">Mark the email to {email} as sent so it moves out of your to-do list.</p>
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onNo} disabled={busy}>
            No, not yet
          </button>
          <button type="button" className="btn-primary" onClick={onYes} disabled={busy}>
            Yes, mark as emailed
          </button>
        </div>
      </div>
    </Modal>
  );
}
