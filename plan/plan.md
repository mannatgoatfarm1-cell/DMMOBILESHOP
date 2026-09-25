# DMobileMart Payments, Wallet & Live Auction Experience

DMobileMart mein secure checkout, wallet top-up aur premium live-auction journey ko ek consistent customer experience mein complete kiya jayega.
Reference ki dark navy, electric blue-magenta aur QC-trust visual language desktop aur mobile dono par follow hogi.

## Who it's for

- Customers jo verified refurbished mobile, laptops aur accessories ko fixed-price ya live auction mein khareedte hain.
- Store admin jo payments, wallet credits, live auctions aur customer support ko ek jagah se manage karta hai.

## Core features and experience

- Razorpay checkout credentials ka secure handling: secret kabhi customer ko nahi dikhega; masked field dobara save hone par existing secret overwrite nahi hoga.
- Customer checkout mein safe Razorpay order creation, payment completion ke baad verification, aur meaningful failure/retry state.
- Wallet Add Money flow: customer amount choose karega, Razorpay checkout complete karega, aur verified payment ke baad hi wallet balance aur transaction history update hogi.
- Admin Live Control Board: pending payment reviews, open support chats, pending returns aur active carts ke live counters aur direct actions.
- Reference-inspired Auction hub: live hero, browsing categories, left-side filters, live auction product grid, timers, current/market price, bid count, QC status, and a ranked trending/leaderboard rail.
- Auction detail and bidding journey: product trust details, current bid, required next bid, quick increment buttons, bid confirmation, highest-bidder live state, and auction-win payment handoff.
- Auction win, payment, order tracking, QC report and post-purchase states will remain connected so customers can move from bid to delivery confidently.

## User flow

1. Customer opens Auction, filters a category or brand, sees live timers and taps an item.
2. Product auction detail shows QC status, pricing, bid history and minimum eligible bid; customer places a valid bid.
3. During the auction, the highest bid and leaderboard refresh live. Winning customer receives a clear payment action and proceeds through the existing secure checkout.
4. For wallet funding, customer chooses Add Money, enters an amount, completes Razorpay payment, and sees the updated available balance only after verification.
5. Admin monitors urgent queues from the Live Control Board and opens the relevant payment, chat, return or cart item directly.

## UI/UX feel

- Supplied reference jaisa premium **Auction Command Center**: black-blue/navy base, luminous electric-blue borders, magenta-to-blue action gradients, and selective green for winning/success states.
- Desktop page will use the same high-information composition: branded search/header and category rail, a wide Live Auction visual banner, process/trending side panels, filter column, dense live-bid cards, leaderboard and trusted-service footer strip.
- Each auction card will make the live state instantly visible through countdown timers, red LIVE markers, large current bid, secondary market price, QC badges, bid totals and a strong gradient Place Bid action.
- The mobile flow will mirror the supplied sequence: auction listing → auction detail → bid amount/increments → live bidder list → auction won → payment → order tracking → QC report → post-purchase confirmation.
- Product images remain prominent, fully visible and carefully cropped; the interface will use real app product/QC/bid data rather than decorative placeholder tiles.
- Interactions will feel responsive and premium: clear hover/pressed states, live-update emphasis, readable empty/loading/error states, and no unnecessary rounded-card clutter.

## Implementation phases

### Phase 1 — Build now
- Fix Razorpay credential persistence and checkout authentication handling without exposing secrets.
- Deliver verified wallet top-ups and balance/ledger updates using Razorpay Test Mode; automated verification will not execute a real charge.
- Add the Admin Live Control Board with payment, chat, return and cart monitoring.
- Rework the Auction hub and bid journey to match the supplied reference's desktop/mobile structure while preserving existing product, QC, bid and order information.

### Phase 2 — Next
- Add auction-watch notifications, saved auctions and clear countdown alerts before an auction closes.
- Add richer wallet transaction filters, downloadable receipts and dedicated payment reconciliation controls.

### Phase 3 — Later
- Add AI deal discovery, Refer & Earn, Bulk Buy and Price Tracker experiences.
- Add production Razorpay webhooks, refund reconciliation and stronger auction close automation after production credentials and approval are available.

## Assumptions

- The provided auction images are a visual reference; the implementation will use the app's existing live catalog, auctions, QC reports and customer data rather than copying static products or people from the images.
- Razorpay Test Mode will be used for wallet top-up verification and all development validation, so no real customer charge is made.
- An admin will enter valid active Razorpay Test Key ID and Key Secret in Admin → Payments before a real provider-order verification can succeed.
- Existing auction rules, current bid data and customer checkout flow will be retained; the requested work enhances their visual hierarchy and end-to-end clarity.
- The preview-gateway external CORS limitation remains outside this scope because same-origin website flows continue to work.