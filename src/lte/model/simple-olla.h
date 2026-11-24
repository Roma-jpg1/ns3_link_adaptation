/*
 * SPDX-License-Identifier: GPL-2.0-only
 */

#ifndef SIMPLE_OLLA_H
#define SIMPLE_OLLA_H

#include "lte-amc.h"

namespace ns3
{

/**
 * Select an MCS using CQI and measured BLER.
 *
 * @param amc AMC object.
 * @param cqi Reported CQI in the range 0 to 15.
 * @param bler Measured BLER in the range 0 to 1.
 * @param upThreshold BLER threshold for increasing MCS.
 * @param downThreshold BLER threshold for decreasing MCS.
 * @param nMcsUp Nonnegative number of steps upward.
 * @param nMcsDown Nonnegative number of steps downward.
 * @return Selected MCS, or -1 for CQI 0.
 */
int SelectMcs(Ptr<LteAmc> amc,
              int cqi,
              double bler,
              double upThreshold,
              double downThreshold,
              double nMcsUp,
              double nMcsDown);

} // namespace ns3

#endif // SIMPLE_OLLA_H
