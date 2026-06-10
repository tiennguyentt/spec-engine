# FlowBook — Kickoff meeting (CTO, PM, Eng Lead)

**Attendees:** Mai (CTO), Tien (PM), Duc (Eng Lead)
**Topic:** Booking + deposit flow for FlowBook v1 (salon booking app)

---

**Mai (CTO):** Let's lock the core decision first. Every booking takes a 20 percent
deposit at the time of booking. No exceptions. We lost too much money on no-shows
last quarter.

**Tien (PM):** Including walk-in conversions? Some salons add walk-ins into the
system after the customer is already in the chair.

**Mai (CTO):** If it goes through the app, it takes a deposit. That's the rule I
want engineering to build against.

**Duc (Eng Lead):** Payment provider?

**Mai (CTO):** We already signed with PayFlow for v1. Card and local wallets.
Refunds have to be automatic, I don't want support tickets for refunds.

**Tien (PM):** Cancellation policy?

**Mai (CTO):** Free cancellation up to 24 hours before the appointment, full
deposit refund. Inside 24 hours the deposit is forfeit. The salon keeps 80 percent
of a forfeited deposit, we keep 20 as platform fee.

**Duc (Eng Lead):** Do salons set their own service durations?

**Mai (CTO):** Yes, per service. But slot granularity is fixed at 15 minutes
platform-wide, otherwise the calendar logic explodes.

**Tien (PM):** Notifications?

**Mai (CTO):** Booking confirmation and a reminder 24 hours before. SMS plus push.
Email is optional for v1, don't block on it.
