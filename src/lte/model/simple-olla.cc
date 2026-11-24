/*
 * SPDX-License-Identifier: GPL-2.0-only
 */

#include "simple-olla.h"

#include <algorithm>

namespace ns3
{

int
SelectMcs(ns3::Ptr<ns3::LteAmc> amc,
          int cqi,
          double bler,
          double upThreshold,
          double downThreshold,
          double nMcsUp,
          double nMcsDown)
{
    if (cqi == 0)
    {
        return -1;
    }

    int mcs = amc->GetMcsFromCqi(cqi);

    if (bler < upThreshold)
    {
        mcs += nMcsUp;
    }
    else if (bler > downThreshold)
    {
        mcs -= nMcsDown;
    }

    return std::clamp(mcs, 0, 28);
}

} // namespace ns3
